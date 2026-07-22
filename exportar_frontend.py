#!/usr/bin/env python3
"""Roda a análise e exporta os dados para o front-end (frontend/dados.js).

Uso:
    python exportar_frontend.py --dados data/exemplo_leilao.csv
"""

import argparse
import json
import pathlib

import joblib

from leilao_ml.config import ConfigCustos
from leilao_ml.dados import carregar_qualquer
from leilao_ml.oportunidades import analisar_oportunidades


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dados", default="data/exemplo_leilao.csv")
    p.add_argument("--modelos", default="modelos")
    p.add_argument("--config", help="JSON com premissas de custo (opcional)")
    p.add_argument("--saida", default="frontend/dados.js")
    p.add_argument("--top", type=int, default=0,
                   help="exporta só as N melhores (0 = todas)")
    args = p.parse_args()

    pasta = pathlib.Path(args.modelos)
    modelo_preco = joblib.load(pasta / "modelo_preco.joblib")
    modelos_tempo = joblib.load(pasta / "modelos_tempo.joblib")
    cfg = ConfigCustos.de_json(args.config) if args.config else ConfigCustos()

    df = carregar_qualquer(args.dados)
    resultado = analisar_oportunidades(df, modelo_preco, modelos_tempo, cfg)
    resultado["classificacao"] = resultado["classificacao"].astype(str)
    if args.top:
        resultado = resultado.head(args.top)

    # só as colunas que o front usa, para manter o arquivo leve
    colunas_front = [
        "id", "cidade", "bairro", "uf", "endereco", "tipo", "padrao_bairro",
        "area_m2", "quartos", "vagas", "ocupado", "aceita_financiamento",
        "modalidade", "link", "valor_avaliacao", "lance_minimo",
        "desconto_vs_avaliacao", "preco_venda_previsto",
        "dias_p25", "dias_p50", "dias_p90", "custo_extras", "custo_posse",
        "investimento_total", "corretagem", "ir_ganho_capital",
        "lucro_liquido", "roi", "retorno_mensal", "score", "classificacao",
    ]
    resultado = resultado[[c for c in colunas_front if c in resultado.columns]]

    payload = {
        "gerado_com": args.dados,
        "premissas": cfg.__dict__,
        "imoveis": json.loads(resultado.to_json(orient="records")),
    }
    saida = pathlib.Path(args.saida)
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(
        "window.DADOS_LEILAO = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"{len(resultado)} imóveis exportados para {saida}")


if __name__ == "__main__":
    main()
