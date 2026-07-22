"""Modelos de previsão: preço de venda e tempo até a venda.

- Preço de venda: HistGradientBoostingRegressor (regressão de mediana,
  robusta a outliers de preço).
- Tempo de venda: três regressores de quantil (P25/P50/P90) para dar
  cenário otimista, esperado e conservador em dias.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAS = ["cidade", "padrao_bairro", "tipo"]
NUMERICAS_PRECO = [
    "area_m2", "quartos", "vagas", "aceita_financiamento", "valor_avaliacao",
]
# o tempo de venda depende também de quão perto do mercado se pretende vender
NUMERICAS_TEMPO = NUMERICAS_PRECO + ["razao_preco_avaliacao"]

QUANTIS_TEMPO = (0.25, 0.50, 0.90)


def _pipeline(numericas: list[str], **kw) -> Pipeline:
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS),
        ("num", "passthrough", numericas),
    ])
    modelo = HistGradientBoostingRegressor(
        max_iter=400, learning_rate=0.06, max_depth=6, random_state=0, **kw
    )
    return Pipeline([("pre", pre), ("modelo", modelo)])


def treinar_modelo_preco(df: pd.DataFrame) -> tuple[Pipeline, dict]:
    """Treina o modelo de preço de venda e devolve (modelo, métricas)."""
    X, y = df, df["preco_venda_real"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=0)
    pipe = _pipeline(NUMERICAS_PRECO, loss="absolute_error")
    pipe.fit(X_tr, y_tr)
    mape = mean_absolute_percentage_error(y_te, pipe.predict(X_te))
    return pipe, {"mape_teste": round(float(mape), 4), "n_treino": len(X_tr)}


def treinar_modelos_tempo(df: pd.DataFrame) -> tuple[dict, dict]:
    """Treina os modelos de quantil do tempo de venda (em dias)."""
    df = df.copy()
    df["razao_preco_avaliacao"] = df["preco_venda_real"] / df["valor_avaliacao"]
    X, y = df, df["dias_ate_venda"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=0)

    modelos = {}
    for q in QUANTIS_TEMPO:
        pipe = _pipeline(NUMERICAS_TEMPO, loss="quantile", quantile=q)
        pipe.fit(X_tr, y_tr)
        modelos[q] = pipe

    mediana = modelos[0.50].predict(X_te)
    mape = mean_absolute_percentage_error(y_te, mediana)
    cobertura_p90 = float(np.mean(y_te <= modelos[0.90].predict(X_te)))
    metricas = {
        "mape_mediana_teste": round(float(mape), 4),
        "cobertura_p90": round(cobertura_p90, 3),
        "n_treino": len(X_tr),
    }
    return modelos, metricas


def prever_tempo(modelos_tempo: dict, df: pd.DataFrame,
                 preco_venda_previsto: np.ndarray) -> pd.DataFrame:
    """Prevê os quantis de dias até a venda para novos imóveis."""
    X = df.copy()
    X["razao_preco_avaliacao"] = preco_venda_previsto / X["valor_avaliacao"]
    out = {}
    for q, pipe in modelos_tempo.items():
        out[f"dias_p{int(q * 100)}"] = np.clip(pipe.predict(X), 7, None).round(0)
    return pd.DataFrame(out, index=df.index)
