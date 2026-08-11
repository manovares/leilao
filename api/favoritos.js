// Favoritos dos visitantes, salvos num Redis (Upstash) conectado à Vercel.
//
// Configuração (uma vez, no painel da Vercel):
//   Projeto -> Storage -> Create Database -> Upstash (Redis, plano free)
//   -> Connect to Project. As variáveis KV_REST_API_URL / KV_REST_API_TOKEN
//   (ou UPSTASH_REDIS_REST_URL / _TOKEN) são criadas automaticamente.
//
// Sem o banco configurado, o site continua funcionando com os favoritos
// salvos apenas no navegador de cada visitante.
//
// API:
//   GET  /api/favoritos?u=<codigo>            -> { favoritos: [ids] }
//   POST /api/favoritos { u, favoritos: [] }  -> { ok, total }

const URL_KV = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const TOKEN_KV = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;

const ACESSOS = new Map();
const JANELA_MS = 10 * 60 * 1000;
const LIMITE = 120;

async function redis(comando) {
  const r = await fetch(URL_KV, {
    method: "POST",
    headers: { Authorization: "Bearer " + TOKEN_KV, "Content-Type": "application/json" },
    body: JSON.stringify(comando),
  });
  if (!r.ok) throw new Error("banco respondeu " + r.status);
  return (await r.json()).result;
}

module.exports = async (req, res) => {
  if (!URL_KV || !TOKEN_KV) {
    return res.status(501).json({
      erro: "banco de favoritos não configurado — adicione um Redis (Upstash) em Storage no projeto da Vercel",
    });
  }

  const ip = String(req.headers["x-forwarded-for"] || "?").split(",")[0].trim();
  const agora = Date.now();
  const hist = (ACESSOS.get(ip) || []).filter(t => agora - t < JANELA_MS);
  if (hist.length >= LIMITE) {
    return res.status(429).json({ erro: "muitas requisições — tente de novo em alguns minutos" });
  }
  hist.push(agora);
  ACESSOS.set(ip, hist);

  const bruto = req.method === "GET" ? (req.query && req.query.u) : (req.body && req.body.u);
  const u = String(bruto || "").toLowerCase().replace(/[^a-z0-9@._-]/g, "").slice(0, 40);
  if (!u) return res.status(400).json({ erro: "informe o código do usuário (u)" });
  const chave = "fav:" + u;

  try {
    if (req.method === "GET") {
      const v = await redis(["GET", chave]);
      return res.status(200).json({ favoritos: v ? JSON.parse(v) : [] });
    }
    if (req.method === "POST") {
      const favs = Array.isArray(req.body && req.body.favoritos)
        ? req.body.favoritos.map(x => String(x).slice(0, 40)).slice(0, 1000)
        : null;
      if (!favs) return res.status(400).json({ erro: "envie { u, favoritos: [...] }" });
      await redis(["SET", chave, JSON.stringify(favs)]);
      return res.status(200).json({ ok: true, total: favs.length });
    }
    return res.status(405).json({ erro: "use GET ou POST" });
  } catch (e) {
    return res.status(502).json({ erro: "falha no banco de favoritos: " + e.message });
  }
};
