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
  "gemini-3.5-flash-lite",
  "gemini-3-flash",
  "gemini-2.5-flash",
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
  const r = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/models/" + modelo +
    ":generateContent?key=" + encodeURIComponent(chave),
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) },
  );
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

// tenta cada modelo; 404/429 pulam para o próximo; se a busca (grounding)
// falhar por outro motivo, tenta o mesmo modelo SEM busca antes de desistir
async function gerarComFallback(chave, prompt, comBusca) {
  let ultimoErro = null;
  for (const modelo of await candidatos(chave)) {
    try {
      return { texto: await gerar(chave, modelo, prompt, comBusca), buscou: comBusca };
    } catch (e) {
      ultimoErro = e;
      if (e.status === 404 || e.status === 429) continue;
      if (comBusca) {
        try {
          const promptSem = prompt + " (Não foi possível pesquisar na internet: estime pelo seu " +
            "conhecimento do mercado local e diga no resumo que é estimativa sem busca.)";
          return { texto: await gerar(chave, modelo, promptSem, false), buscou: false };
        } catch (e2) {
          ultimoErro = e2;
          if (e2.status === 404 || e2.status === 429) continue;
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
    return res.status(502).json({ erro: String(e.message || e).slice(0, 200) });
  }
};
