#!/usr/bin/env python3
"""Analisa um CSV de imóveis de leilão e ranqueia as melhores oportunidades.

Uso:
    python analisar.py --dados data/exemplo_leilao.csv
    python analisar.py --dados edital.csv --config custos.json --top 20
"""

import argparse
import pathlib

import joblib

from leilao_ml.config import ConfigCustos
from leilao_ml.dados import carregar_csv
from leilao_ml.oportunidades import analisar_oportunidades, imprimir_relatorio


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dados", required=True, help="CSV com os lotes do leilão")
    p.add_argument("--modelos", default="modelos", help="pasta com os modelos treinados")
    p.add_argument("--config", help="JSON com premissas de custo (opcional)")
    p.add_argument("--top", type=int, default=15, help="quantas oportunidades exibir")
    p.add_argument("--saida", default="resultado_oportunidades.csv",
                   help="CSV de saída com o ranking completo")
    args = p.parse_args()

    pasta = pathlib.Path(args.modelos)
    if not (pasta / "modelo_preco.joblib").exists():
        raise SystemExit(f"Modelos não encontrados em {pasta}/. Rode antes: python treinar.py")

    modelo_preco = joblib.load(pasta / "modelo_preco.joblib")
    modelos_tempo = joblib.load(pasta / "modelos_tempo.joblib")
    cfg = ConfigCustos.de_json(args.config) if args.config else ConfigCustos()

    df = carregar_csv(args.dados)
    resultado = analisar_oportunidades(df, modelo_preco, modelos_tempo, cfg)
    resultado.to_csv(args.saida, index=False)

    print(f"\n{len(df)} imóveis analisados — top {args.top} oportunidades "
          f"(ranking completo em {args.saida}):\n")
    imprimir_relatorio(resultado, args.top)


if __name__ == "__main__":
    main()
