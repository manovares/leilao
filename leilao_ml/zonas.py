"""Classificação de zonas da cidade de São Paulo a partir do bairro/endereço.

Hoje cobre a Zona Leste (pedido do usuário: sempre destacar esses imóveis).
A identificação é por distrito/bairro conhecido, com casamento por palavra
inteira, e só se aplica quando a cidade é São Paulo (capital).
"""

import unicodedata

import pandas as pd

DISTRITOS_ZONA_LESTE = [
    "agua rasa", "analia franco", "aricanduva", "artur alvim", "belem",
    "burgo paulista", "cangaiba", "carrao", "cidade lider",
    "cidade tiradentes", "cidade a e carvalho", "a e carvalho",
    "ermelino matarazzo", "guaianases", "guaianazes", "iguatemi",
    "itaim paulista", "itaquera", "jardim helena", "jose bonifacio",
    "lajeado", "mooca", "parque do carmo", "penha", "ponte rasa",
    "sao lucas", "sao mateus", "sao miguel", "sao rafael", "sapopemba",
    "tatuape", "teotonio vilela", "vila antonieta", "vila curuca",
    "vila esperanca", "vila formosa", "vila jacui", "vila matilde",
    "vila prudente", "vila re",
]


def _norm(s: str) -> str:
    s = "".join(
        c for c in unicodedata.normalize("NFD", str(s).lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.split())


def eh_zona_leste(cidade: str, bairro: str = "", endereco: str = "") -> bool:
    if "sao paulo" not in _norm(cidade):
        return False
    texto = f" {_norm(bairro)} | {_norm(endereco)} "
    return any(f" {d} " in texto for d in DISTRITOS_ZONA_LESTE)


def marcar_zona_leste(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona a coluna booleana `zona_leste` ao DataFrame do pipeline."""
    bairro = df["bairro"] if "bairro" in df.columns else ""
    endereco = df["endereco"] if "endereco" in df.columns else ""
    df["zona_leste"] = [
        eh_zona_leste(c, b, e)
        for c, b, e in zip(
            df["cidade"],
            bairro if hasattr(bairro, "__iter__") and not isinstance(bairro, str) else [""] * len(df),
            endereco if hasattr(endereco, "__iter__") and not isinstance(endereco, str) else [""] * len(df),
        )
    ]
    return df
