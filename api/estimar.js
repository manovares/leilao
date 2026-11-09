// Função serverless da Vercel: consulta o Gemini usando a chave do SERVIDOR,
// para que qualquer visitante do site use a estimativa por IA sem ter chave.
//
// Configuração (uma vez, no painel da Vercel):
//   Projeto -> Settings -> Environment Variables -> adicionar
//   GEMINI_API_KEY = sua chave do Google AI Studio (AIza...)
//
// A chave nunca aparece no navegador — fica só aqui no servidor.
//
// Os modelos do Google mudam de nome com o tempo (os 2.x foram desligados
// em 2026). Por isso a lista abaixo é só o ponto de partida: se nenhum nome
// fixo funcionar, o servidor DESCOBRE os modelos disponíveis na própria API
// e usa o flash mais novo — assim não quebra de novo quando o Google renomear.

const MODELOS_FIXOS = [
  "gemini-flash-latest",   // apelido oficial: sempre aponta para o flash estável
  "gemini-3.8-flash",
  "gemini-3.5-flash",
  "gemini-3-flash-preview",
  "gemini-3.5-flash-lite", // por último: nem sempre suporta busca
];

let MODELOS_DESCOBERTOS = null;

async function descobrirModelos(chave) {
  if (MODELOS_DESCOBERTOS) return MODELOS_DESCOBERTOS;
  try {
    const r = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=" +
      encodeURIComponent(chave),
    );
    if (!r.ok) return [];
    const j = await r.json();
    const nomes = (j.models || [])
      .filter(m => (m.supportedGenerationMethods || []).includes("generateContent"))
      .map(m => String(m.name || "").replace("models/", ""))
      .filter(n => n.includes("flash") &&
        !/image|tts|live|audio|embedding|nano|banana|preview-\d{2}/.test(n));
    const versao = n => parseFloat((n.match(/(\d+(?:\.\d+)?)/) || [0, 0])[1]) || 0;
    nomes.sort((a, b) => versao(b) - versao(a));
    MODELOS_DESCOBERTOS = nomes.slice(0, 6);
    return MODELOS_DESCOBERTOS;
  } catch (e) {
    return [];
  }
}

async function candidatos(chave) {
  return [...new Set([...MODELOS_FIXOS, ...(await descobrirModelos(chave))])];
}

async function gerar(chave, modelo, prompt, comBusca) {
  const corpo = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.2 },
  };
  if (comBusca) corpo.tools = [{ google_search: {} }];
  else corpo.generationConfig.responseMimeType = "application/json";
  // nunca deixa uma chamada pendurar: 20s e aborta (vira erro visível)
  const r = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/models/" + modelo +
    ":generateContent?key=" + encodeURIComponent(chave),
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo), signal: AbortSignal.timeout(20000) },
  ).catch(err => {
    const e = new Error("Gemini (" + modelo + ") não respondeu em 20s");
    e.status = 408;
    throw err && err.name === "TimeoutError" ? e : err;
  });
  if (!r.ok) {
    const e = new Error("Gemini (" + modelo + ") respondeu " + r.status);
    e.status = r.status;
    throw e;
  }
  const j = await r.json();
  const partes = (j.candidates && j.candidates[0] && j.candidates[0].content &&
    j.candidates[0].content.parts) || [];
  return partes.map(p => p.text || "").join("");
}

// tenta os primeiros modelos; 404 pula para o próximo; na busca, 400
// (sem suporte a grounding) também pula, e QUALQUER outra falha — 429 de
// cota de pesquisa incluído — tenta o mesmo modelo SEM busca, porque a
// cota de geração costuma existir mesmo quando a de pesquisa acaba
let CAMINHO_BOM = { buscado: null, direto: null }; // memória por instância

async function gerarComFallback(chave, prompt, comBusca) {
  let ultimoErro = null;
  // atalho: reusa o que funcionou na última chamada (economiza ~30s por lote)
  const memo = comBusca ? CAMINHO_BOM.buscado : CAMINHO_BOM.direto;
  if (memo) {
    try {
      return { texto: await gerar(chave, memo.modelo, memo.buscou ? prompt
        : prompt + " (Não foi possível pesquisar na internet: estime pelo seu conhecimento do mercado local e diga no resumo que é estimativa sem busca.)",
        memo.buscou), buscou: memo.buscou };
    } catch (e) { /* memória desatualizada: segue o caminho completo */ }
  }
  for (const modelo of (await candidatos(chave)).slice(0, 5)) {
    try {
      const texto = await gerar(chave, modelo, prompt, comBusca);
      if (comBusca) CAMINHO_BOM.buscado = { modelo, buscou: true };
      else CAMINHO_BOM.direto = { modelo, buscou: false };
      return { texto, buscou: comBusca };
    } catch (e) {
      ultimoErro = e;
      if (e.status === 404) continue;
      if (!comBusca && e.status === 429) continue;
      if (comBusca && e.status === 400) continue;
      if (comBusca) {
        try {
          const promptSem = prompt + " (Não foi possível pesquisar na internet: estime pelo seu " +
            "conhecimento do mercado local e diga no resumo que é estimativa sem busca.)";
          const texto = await gerar(chave, modelo, promptSem, false);
          if (comBusca) CAMINHO_BOM.buscado = { modelo, buscou: false };
          return { texto, buscou: false };
        } catch (e2) {
          ultimoErro = e2;
          continue; // tenta o próximo modelo
        }
      }
    }
  }
  throw ultimoErro || new Error("nenhum modelo Gemini disponível");
}

// proteção simples contra abuso: 30 consultas por IP a cada 10 minutos
const ACESSOS = new Map();
const JANELA_MS = 10 * 60 * 1000;
const LIMITE = 30;

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    return res.status(405).json({ erro: "use POST" });
  }
  const chave = process.env.GEMINI_API_KEY;
  if (!chave) {
    return res.status(500).json({
      erro: "GEMINI_API_KEY não configurada nas variáveis de ambiente da Vercel",
    });
  }

  const ip = String(req.headers["x-forwarded-for"] || "?").split(",")[0].trim();
  const agora = Date.now();
  const hist = (ACESSOS.get(ip) || []).filter(t => agora - t < JANELA_MS);
  if (hist.length >= LIMITE) {
    return res.status(429).json({ erro: "muitas consultas — tente de novo em alguns minutos" });
  }
  hist.push(agora);
  ACESSOS.set(ip, hist);

  // diagnóstico: mostra o que o servidor consegue fazer com a chave atual
  if (req.body && req.body.diag === true) {
    const lista = (await candidatos(chave)).slice(0, 3); // só os 3 primeiros p/ caber no tempo
    const diag = { modelos: lista, geracao: null, busca: null };
    for (const m of lista) {
      try {
        await gerar(chave, m, 'Responda SOMENTE com o JSON {"ok": true}', false);
        diag.geracao = "ok (" + m + ")";
        break;
      } catch (e) { diag.geracao = String(e.message || e).slice(0, 140); }
    }
    for (const m of lista) {
      try {
        await gerar(chave, m, 'Pesquise na internet a cotação atual do dólar e responda SOMENTE com o JSON {"ok": true}', true);
        diag.busca = "ok com pesquisa Google (" + m + ")";
        break;
      } catch (e) { diag.busca = String(e.message || e).slice(0, 140); }
    }
    return res.status(200).json(diag);
  }

  const soTexto = v => Array.isArray(v) ? v.filter(x => typeof x === "string").slice(0, 150) : [];
  const regioes = soTexto(req.body && req.body.regioes);
  const imoveis = soTexto(req.body && req.body.imoveis);
  const condominio = typeof (req.body && req.body.condominio) === "string"
    ? req.body.condominio.slice(0, 300) : "";
  const portal = typeof (req.body && req.body.portal) === "string"
    ? req.body.portal.slice(0, 300) : "";
  if (!regioes.length && !imoveis.length && !condominio && !portal) {
    return res.status(400).json({ erro: "envie { regioes }, { imoveis }, { condominio } ou { portal }" });
  }

  try {
    // buscas com grounding (pesquisa Google) devolvem texto cru para o front
    if (condominio || portal) {
      const promptCond = condominio
        ? "Pesquise na internet apartamentos à venda ou vendidos recentemente NO MESMO " +
          "condomínio/empreendimento deste endereço: " + condominio + ". Encontre o preço mais recente " +
          "(venda ou anúncio). IGNORE anúncios de leilão, arremate ou venda judicial — considere apenas " +
          'o mercado tradicional. Responda SOMENTE com JSON: {"valor": número em reais ou null, ' +
          '"resumo": "frase curta com o que encontrou e a fonte"}.'
        : "Pesquise anúncios de VENDA de imóveis usados nos portais brasileiros vivareal.com.br, " +
          "zapimoveis.com.br, quintoandar.com.br, imovelweb.com.br e olx.com.br, semelhantes a este " +
          "(mesmo bairro ou condomínio, tipo e tamanho parecidos): " + portal + ". " +
          "IGNORE COMPLETAMENTE qualquer anúncio de leilão, arremate ou venda judicial publicado nesses sites. " +
          "Com base apenas nos anúncios comuns encontrados, estime o valor de venda deste imóvel. " +
          'Responda SOMENTE com JSON: {"valor": número em reais ou null, ' +
          '"resumo": "frase curta com os anúncios usados de referência e o portal"}.';
      const saida = await gerarComFallback(chave, promptCond, true);
      return res.status(200).json({ resultado: saida.texto, buscou: saida.buscou });
    }

    const SEM_LEILAO = "IMPORTANTE: considere APENAS o mercado tradicional (anúncios e vendas comuns); " +
      "NÃO use como base preços de imóveis de leilão, arremate ou venda judicial — " +
      "são descontados e distorcem a referência. ";
    const prompt = regioes.length
      ? "Você é um avaliador imobiliário brasileiro. Estime o preço médio de VENDA por metro " +
        "quadrado (R$/m²) de APARTAMENTOS USADOS em cada região abaixo, em valores atuais e " +
        "realistas de mercado. " + SEM_LEILAO +
        'Responda SOMENTE com JSON válido: um array de objetos ' +
        '{"chave": string, "preco_m2": number}. Não escreva mais nada.\nRegiões:\n- ' +
        regioes.join("\n- ")
      : "Você é um avaliador imobiliário brasileiro. Estime o valor de VENDA de mercado " +
        "(em reais) de cada imóvel usado abaixo, realista para a localização e o tipo. " + SEM_LEILAO +
        'Responda SOMENTE com JSON válido: um array de objetos {"id": string, "valor": number}. ' +
        "Não escreva mais nada.\nImóveis:\n- " + imoveis.join("\n- ");
    const saida = await gerarComFallback(chave, prompt, false);
    try {
      return res.status(200).json({ precos: JSON.parse(saida.texto || "") });
    } catch (e) {
      return res.status(502).json({ erro: "resposta inválida da IA" });
    }
  } catch (e) {
    const msg = String(e.message || e);
    if (/respondeu 429/.test(msg)) {
      return res.status(502).json({
        erro: "Cota da chave do Google esgotada (429). A cota gratuita renova todo dia; " +
          "para uso maior, ative o faturamento da chave no Google AI Studio (custa centavos por busca).",
        cota: true,
      });
    }
    return res.status(502).json({ erro: msg.slice(0, 200) });
  }
};
