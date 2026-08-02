"""Leitura da planilha do Arrematador (agregador de leilões).

Formato esperado (cabeçalho): ID IMOVEL; MODALIDADE; TIPO IMOVEL; ESTADO;
CIDADE; ENDERECO; VALOR AVALIAÇÃO; VALOR DE VENDA; DESCONTO;
ACEITA FINANCIAMENTO; ACEITA FGTS; DESCRICAO; DATA LEILÃO; LINK.
Valores monetários no padrão brasileiro ("R$ 475.000,00").
Converte para o esquema do pipeline (ver `leilao_ml/dados.py`).
"""

import io
import re
import unicodedata

import pandas as pd

from .caixa import MAPA_TIPO

MAPA_TIPO_EXTRA = {
    "gleba urbana": "terreno",
    "gleba": "terreno",
    "imovel rural": "terreno",
    "loja": "comercial",
    "outros": "casa",
}


def _sem_acento(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s).lower())
        if unicodedata.category(c) != "Mn"
    )


def _ler_texto(caminho: str) -> str:
    try:
        texto = open(caminho, encoding="utf-8").read()
        if "�" in texto:
            raise UnicodeError
        return texto
    except UnicodeError:
        return open(caminho, encoding="latin-1").read()


def eh_planilha_arrematador(caminho: str) -> bool:
    with open(caminho, "rb") as f:
        inicio = _sem_acento(f.read(4096).decode("latin-1", errors="ignore"))
    return "valor de venda" in inicio and ("fgts" in inicio or "data leilao" in inicio)


def _numero_br(s: pd.Series) -> pd.Series:
    limpo = s.astype(str).str.replace(r"[^\d.,\-]", "", regex=True)
    return pd.to_numeric(
        limpo.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def carregar_arrematador(caminho: str, ocupado_padrao: int = 1) -> pd.DataFrame:
    """Lê a planilha do Arrematador e devolve o esquema do pipeline."""
    texto = _ler_texto(caminho)
    linhas = texto.splitlines()
    ix = next(
        (i for i, l in enumerate(linhas) if "valor de venda" in _sem_acento(l)), 0
    )
    corpo = "\n".join(linhas[ix:])
    sep = ";" if corpo.splitlines()[0].count(";") >= corpo.splitlines()[0].count(",") else ","
    bruto = pd.read_csv(io.StringIO(corpo), sep=sep, dtype=str)
    bruto.columns = [_sem_acento(c).strip() for c in bruto.columns]

    def col(nome):
        alvo = next((c for c in bruto.columns if nome in c), None)
        return bruto[alvo] if alvo is not None else pd.Series("", index=bruto.index)

    desc = col("descricao").fillna("").astype(str).map(_sem_acento)

    def extrai(padrao):
        return pd.to_numeric(desc.str.extract(padrao)[0], errors="coerce")

    tipo_bruto = col("tipo").fillna("").astype(str).map(_sem_acento).str.strip()
    tipo = tipo_bruto.map(lambda t: MAPA_TIPO_EXTRA.get(t) or MAPA_TIPO.get(t, "casa"))

    area = pd.to_numeric(
        desc.str.replace("²", "2").str.extract(r"([\d]+[.,]?\d*)\s*m2")[0]
        .str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0.0)

    df = pd.DataFrame({
        "id": col("id").astype(str).str.strip(),
        "cidade": col("cidade").astype(str).str.strip().str.title(),
        "padrao_bairro": "medio",
        "tipo": tipo,
        "area_m2": area.round(1),
        "quartos": extrai(r"(\d+)\s*(?:qto|quarto)").fillna(0).astype(int),
        "vagas": extrai(r"(\d+)\s*vaga").fillna(0).astype(int),
        "ocupado": ocupado_padrao,
        "aceita_financiamento": col("financiamento").astype(str).str.strip()
            .map(_sem_acento).eq("sim").astype(int),
        "aceita_fgts": col("fgts").astype(str).str.strip()
            .map(_sem_acento).eq("sim").astype(int),
        "valor_avaliacao": _numero_br(col("avalia")),
        "lance_minimo": _numero_br(col("valor de venda")),
        "uf": col("estado").astype(str).str.strip(),
        "endereco": col("endereco").astype(str).str.strip(),
        "modalidade": col("modalidade").astype(str).str.strip(),
        "data_leilao": col("data leilao").astype(str).str.strip(),
        "link": col("link").astype(str).str.strip(),
    })
    df = df.dropna(subset=["valor_avaliacao", "lance_minimo"])
    df = df[(df["valor_avaliacao"] > 0) & (df["lance_minimo"] > 0)]

    from .zonas import marcar_zona_leste
    return marcar_zona_leste(df.reset_index(drop=True))
