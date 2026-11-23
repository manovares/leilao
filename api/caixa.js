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

  try {
    const r = await fetch(
      "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_" + uf + ".csv",
      {
        headers: {
          // o site da Caixa recusa clientes sem cara de navegador
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
          "Accept": "text/csv,text/plain,*/*",
          "Referer": "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp",
        },
        signal: AbortSignal.timeout(45000),
      },
    );
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
