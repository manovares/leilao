#!/usr/bin/env python3
"""Treina os modelos de preço de venda e tempo de venda.

Uso:
    python treinar.py                          # treina com dados sintéticos de demonstração
    python treinar.py --dados historico.csv    # treina com seu histórico real de operações
"""

import argparse
import pathlib

import joblib

from leilao_ml.dados import carregar_csv, gerar_dados_sinteticos
from leilao_ml.modelos import treinar_modelo_preco, treinar_modelos_tempo


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dados", help="CSV com histórico real (ver leilao_ml/dados.py)")
    p.add_argument("--saida", default="modelos", help="pasta para salvar os modelos")
    p.add_argument("--n-sintetico", type=int, default=4000,
                   help="tamanho da base sintética quando --dados não é passado")
    args = p.parse_args()

    if args.dados:
        df = carregar_csv(args.dados, treino=True)
        print(f"Histórico real carregado: {len(df)} operações")
    else:
        df = gerar_dados_sinteticos(args.n_sintetico)
        print(f"AVISO: treinando com {len(df)} operações SINTÉTICAS de demonstração.")
        print("Use --dados historico.csv assim que tiver operações reais.\n")

    modelo_preco, met_preco = treinar_modelo_preco(df)
    print(f"Modelo de preço  -> erro médio (MAPE): {met_preco['mape_teste']:.1%}")

    modelos_tempo, met_tempo = treinar_modelos_tempo(df)
    print(f"Modelo de tempo  -> erro mediana (MAPE): {met_tempo['mape_mediana_teste']:.1%}"
          f" | cobertura P90: {met_tempo['cobertura_p90']:.0%}")

    saida = pathlib.Path(args.saida)
    saida.mkdir(exist_ok=True)
    joblib.dump(modelo_preco, saida / "modelo_preco.joblib")
    joblib.dump(modelos_tempo, saida / "modelos_tempo.joblib")
    print(f"\nModelos salvos em {saida}/")


if __name__ == "__main__":
    main()
