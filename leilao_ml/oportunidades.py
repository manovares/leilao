"""Ranqueamento de oportunidades: junta previsões de preço, tempo e custos."""

import numpy as np
import pandas as pd

from .config import ConfigCustos
from .custos import calcular_operacao
from .modelos import prever_tempo


def analisar_oportunidades(df: pd.DataFrame, modelo_preco, modelos_tempo,
                           cfg: ConfigCustos | None = None) -> pd.DataFrame:
    """Analisa um lote de imóveis de leilão e devolve o ranking completo.

    Para cada imóvel calcula:
    - preco_venda_previsto: preço estimado de revenda (pós-reforma)
    - dias_p25 / dias_p50 / dias_p90: cenários de tempo até vender
    - investimento_total e lucro_liquido (cenário base P50)
    - roi, retorno_mensal (no cenário conservador P90) e score 0-100
    """
    cfg = cfg or ConfigCustos()
    df = df.reset_index(drop=True).copy()

    preco_previsto = modelo_preco.predict(df)
    tempos = prever_tempo(modelos_tempo, df, preco_previsto)
    meses_p50 = tempos["dias_p50"].to_numpy() / 30.0
    meses_p90 = tempos["dias_p90"].to_numpy() / 30.0

    op = calcular_operacao(df, preco_previsto, meses_p50, cfg)

    roi = op["lucro_liquido"] / op["investimento_total"]
    # retorno mensalizado no cenário conservador de prazo (P90):
    # penaliza imóveis que podem travar capital por muito tempo
    retorno_mensal = (1 + roi.clip(lower=-0.99)) ** (1 / np.maximum(meses_p90, 1)) - 1

    resultado = pd.concat([df, tempos, op], axis=1)
    resultado["preco_venda_previsto"] = preco_previsto.round(0)
    resultado["desconto_vs_avaliacao"] = (
        1 - df["lance_minimo"] / df["valor_avaliacao"]
    ).round(3)
    resultado["roi"] = roi.round(3)
    resultado["retorno_mensal"] = retorno_mensal.round(4)

    # score 0-100: percentil do retorno mensal dentro do lote analisado
    resultado["score"] = (resultado["retorno_mensal"].rank(pct=True) * 100).round(1)
    resultado["classificacao"] = pd.cut(
        resultado["retorno_mensal"],
        bins=[-np.inf, 0.0, 0.01, 0.025, np.inf],
        labels=["evitar", "regular", "boa", "excelente"],
    )
    return resultado.sort_values("retorno_mensal", ascending=False)


COLUNAS_RELATORIO = [
    "id", "cidade", "tipo", "area_m2", "lance_minimo", "desconto_vs_avaliacao",
    "preco_venda_previsto", "investimento_total", "lucro_liquido",
    "roi", "dias_p50", "dias_p90", "retorno_mensal", "score", "classificacao",
]


def imprimir_relatorio(resultado: pd.DataFrame, top: int = 15) -> None:
    """Imprime as melhores oportunidades no terminal."""
    vis = resultado[COLUNAS_RELATORIO].head(top).copy()
    for col in ["lance_minimo", "preco_venda_previsto",
                "investimento_total", "lucro_liquido"]:
        vis[col] = vis[col].map(lambda v: f"R$ {v:,.0f}".replace(",", "."))
    vis["roi"] = (resultado["roi"].head(top) * 100).map("{:.1f}%".format)
    vis["retorno_mensal"] = (
        resultado["retorno_mensal"].head(top) * 100
    ).map("{:.2f}% a.m.".format)
    vis["desconto_vs_avaliacao"] = (
        resultado["desconto_vs_avaliacao"].head(top) * 100
    ).map("{:.0f}%".format)
    with pd.option_context("display.width", 220, "display.max_columns", None):
        print(vis.to_string(index=False))
