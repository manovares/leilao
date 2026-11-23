// Busca direta, sem planilha: baixa a lista oficial de imóveis da Caixa
// (venda-imoveis.caixa.gov.br) para a UF pedida e devolve o CSV já em UTF-8.
// O navegador não consegue baixar direto por causa de CORS — o servidor sim.

const UFS = new Set(("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI " +
  "RJ RN RS RO RR SC SP SE TO").split(" "));

// cache por instância: a lista muda poucas vezes ao dia
const CACHE = new Map(); // uf -> { em, csv }
const CACHE_MS = 30 * 60 * 1000;

const ACESSOS = new Map();
const JANELA_MS = 10 * 60 * 1000;
const LIMITE = 30;

module.exports = async (req, res) => {
  const uf = String((req.query && req.query.uf) || "SP").toUpperCase();
  if (!UFS.has(uf)) return res.status(400).json({ erro: "UF inválida" });

  const ip = String(req.headers["x-forwarded-for"] || "?").split(",")[0].trim();
  const agora = Date.now();
  const hist = (ACESSOS.get(ip) || []).filter(t => agora - t < JANELA_MS);
  if (hist.length >= LIMITE) {
    return res.status(429).json({ erro: "muitas consultas — tente de novo em alguns minutos" });
  }
  hist.push(agora);
  ACESSOS.set(ip, hist);

  const emCache = CACHE.get(uf);
  if (emCache && agora - emCache.em < CACHE_MS) {
    res.setHeader("Content-Type", "text/csv; charset=utf-8");
    res.setHeader("X-Fonte", "cache");
    return res.status(200).send(emCache.csv);
  }

  const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
  const COMUNS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,text/csv,text/plain,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
  };
  try {
    // 1) visita a página de download para receber os cookies do site
    let cookies = "";
    try {
      const r0 = await fetch("https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp", {
        headers: COMUNS, signal: AbortSignal.timeout(30000), redirect: "follow",
      });
      cookies = (r0.headers.getSetCookie ? r0.headers.getSetCookie() : [])
        .map(c => c.split(";")[0]).join("; ");
      if (req.query && req.query.debug) {
        var dbg = { pagina: r0.status, cookies: cookies ? cookies.split("; ").map(c => c.split("=")[0]) : [] };
      }
    } catch (e) { /* sem cookies: tenta mesmo assim */ }

    // 2) baixa o CSV com os cookies e o referer corretos
    const r = await fetch(
      "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_" + uf + ".csv",
      {
        headers: {
          ...COMUNS,
          "Referer": "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp",
          ...(cookies ? { "Cookie": cookies } : {}),
        },
        signal: AbortSignal.timeout(45000),
      },
    );
    if (req.query && req.query.debug) {
      return res.status(200).json({ ...(dbg || {}), csv_status: r.status,
        tipo: r.headers.get("content-type") });
    }
    if (!r.ok) {
      return res.status(502).json({ erro: "o site da Caixa respondeu " + r.status + " — tente de novo em instantes" });
    }
    const bruto = Buffer.from(await r.arrayBuffer());
    // a lista vem em ISO-8859-1; convertemos para UTF-8 para o navegador
    let csv = bruto.toString("latin1");
    if (!/avalia/i.test(csv.slice(0, 4000))) {
      return res.status(502).json({ erro: "a Caixa devolveu um conteúdo inesperado (não parece a lista de imóveis)" });
    }
    CACHE.set(uf, { em: agora, csv });
    res.setHeader("Content-Type", "text/csv; charset=utf-8");
    res.setHeader("X-Fonte", "caixa");
    return res.status(200).send(csv);
  } catch (e) {
    const msg = e && e.name === "TimeoutError"
      ? "o site da Caixa demorou demais para responder — tente de novo"
      : String((e && e.message) || e).slice(0, 180);
    return res.status(502).json({ erro: msg });
  }
};
