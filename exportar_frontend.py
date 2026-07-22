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
from leilao_ml.dados import carregar_csv
from leilao_ml.oportunidades import analisar_oportunidades


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dados", default="data/exemplo_leilao.csv")
    p.add_argument("--modelos", default="modelos")
    p.add_argument("--config", help="JSON com premissas de custo (opcional)")
    p.add_argument("--saida", default="frontend/dados.js")
    args = p.parse_args()

    pasta = pathlib.Path(args.modelos)
    modelo_preco = joblib.load(pasta / "modelo_preco.joblib")
    modelos_tempo = joblib.load(pasta / "modelos_tempo.joblib")
    cfg = ConfigCustos.de_json(args.config) if args.config else ConfigCustos()

    df = carregar_csv(args.dados)
    resultado = analisar_oportunidades(df, modelo_preco, modelos_tempo, cfg)
    resultado["classificacao"] = resultado["classificacao"].astype(str)

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
