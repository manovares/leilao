// Função serverless da Vercel: consulta o Gemini usando a chave do SERVIDOR,
// para que qualquer visitante do site use a estimativa por IA sem ter chave.
//
// Configuração (uma vez, no painel da Vercel):
//   Projeto -> Settings -> Environment Variables -> adicionar
//   GEMINI_API_KEY = sua chave do Google AI Studio (AIza...)
//
// A chave nunca aparece no navegador — fica só aqui no servidor.

const MODELOS = [
  "gemini-2.5-flash",
  "gemini-3-flash-preview",
  "gemini-2.0-flash",
  "gemini-1.5-flash",
];

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

  const regioes = Array.isArray(req.body && req.body.regioes)
    ? req.body.regioes.filter(r => typeof r === "string").slice(0, 150)
    : [];
  if (!regioes.length) {
    return res.status(400).json({ erro: "envie { regioes: [\"chave \\\"...\\\": descrição\", ...] }" });
  }

  const prompt =
    "Você é um avaliador imobiliário brasileiro. Estime o preço médio de VENDA por metro " +
    "quadrado (R$/m²) de APARTAMENTOS USADOS em cada região abaixo, em valores atuais e " +
    'realistas de mercado. Responda SOMENTE com JSON válido: um array de objetos ' +
    '{"chave": string, "preco_m2": number}. Não escreva mais nada.\nRegiões:\n- ' +
    regioes.join("\n- ");

  for (const modelo of MODELOS) {
    const r = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" + modelo +
      ":generateContent?key=" + encodeURIComponent(chave),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { responseMimeType: "application/json", temperature: 0.2 },
        }),
      },
    );
    if (r.status === 404) continue; // modelo indisponível: tenta o próximo
    if (!r.ok) {
      return res.status(502).json({ erro: "Gemini respondeu " + r.status });
    }
    const j = await r.json();
    const texto = j.candidates && j.candidates[0] && j.candidates[0].content &&
      j.candidates[0].content.parts && j.candidates[0].content.parts[0].text;
    try {
      return res.status(200).json({ precos: JSON.parse(texto || "") });
    } catch (e) {
      return res.status(502).json({ erro: "resposta inválida da IA" });
    }
  }
  return res.status(502).json({ erro: "nenhum modelo Gemini disponível" });
};
