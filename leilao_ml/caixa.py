"""Leitura da 'Lista de Imóveis da Caixa' (CSV oficial de venda-imoveis.caixa.gov.br).

O arquivo vem em ISO-8859-1, com uma linha de banner antes do cabeçalho e os
campos separados por ';'. Tipo, áreas, quartos e vagas vêm dentro do campo
'Descrição'. Este módulo converte tudo para o esquema do pipeline
(ver `leilao_ml/dados.py`), preservando colunas informativas extras
(bairro, endereço, modalidade de venda, link).
"""

import io
import re

import pandas as pd

MAPA_TIPO = {
    "apartamento": "apartamento",
    "casa": "casa",
    "sobrado": "casa",
    "terreno": "terreno",
    "gleba": "terreno",
    "predio": "comercial",
    "prédio": "comercial",
    "galpao": "comercial",
    "galpão": "comercial",
    "sala": "comercial",
    "loja": "comercial",
    "comercial": "comercial",
    "imovel": "casa",
}


def eh_planilha_caixa(caminho: str) -> bool:
    """Detecta o CSV da Caixa pelo banner ou pelo cabeçalho com ';'."""
    with open(caminho, "rb") as f:
        inicio = f.read(4096).decode("latin-1", errors="ignore").lower()
    return "lista de imóveis da caixa" in inicio or (
        "valor de avalia" in inicio and ";" in inicio
    )


def _numero_br(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _extrair_descricao(desc: pd.Series) -> pd.DataFrame:
    """Extrai tipo, área, quartos e vagas do texto de 'Descrição'."""
    desc = desc.fillna("").astype(str)
    tipo_bruto = desc.str.split(",").str[0].str.strip().str.lower()
    tipo = tipo_bruto.map(lambda t: MAPA_TIPO.get(t, "casa"))

    def area_de(padrao):
        # na Descrição os decimais vêm com ponto ("45.46"), sem milhar
        a = desc.str.extract(padrao, flags=re.I)[0]
        return pd.to_numeric(
            a.str.replace(",", ".", regex=False), errors="coerce"
        ).fillna(0.0)

    privativa = area_de(r"([\d.,]+) de área privativa")
    total = area_de(r"([\d.,]+) de área total")
    terreno = area_de(r"([\d.,]+) de área do terreno")
    # área do terreno só vale como fallback para terrenos: em apartamentos
    # ela costuma ser a área do condomínio inteiro e distorce tudo
    area = privativa.where(privativa > 0, total)
    area = area.where((area > 0) | (tipo != "terreno"), terreno)

    quartos = pd.to_numeric(desc.str.extract(r"(\d+) qto")[0], errors="coerce")
    vagas = pd.to_numeric(desc.str.extract(r"(\d+) vaga")[0], errors="coerce")
    return pd.DataFrame({
        "tipo": tipo,
        "area_m2": area.round(1),
        "quartos": quartos.fillna(0).astype(int),
        "vagas": vagas.fillna(0).astype(int),
    })


def carregar_caixa(caminho: str, ocupado_padrao: int = 1) -> pd.DataFrame:
    """Lê a lista da Caixa e devolve um DataFrame no esquema do pipeline.

    `ocupado_padrao`: a lista não informa ocupação; por padrão assumimos 1
    (ocupado) para que o custo de desocupação entre de forma conservadora.
    """
    try:
        texto = open(caminho, encoding="utf-8").read()
        if "�" in texto:
            raise UnicodeError
    except UnicodeError:
        texto = open(caminho, encoding="latin-1").read()

    linhas = texto.splitlines()
    ix = next(
        (i for i, l in enumerate(linhas) if "valor de avalia" in l.lower()), None
    )
    if ix is None:
        raise ValueError("Cabeçalho da lista da Caixa não encontrado no arquivo.")
    bruto = pd.read_csv(io.StringIO("\n".join(linhas[ix:])), sep=";", dtype=str)
    bruto.columns = [c.strip() for c in bruto.columns]

    def col(nome):
        alvo = next((c for c in bruto.columns if nome in c.lower()), None)
        return bruto[alvo] if alvo is not None else pd.Series("", index=bruto.index)

    df = _extrair_descricao(col("descri"))
    df.insert(0, "id", col("imóvel").fillna(col("imovel")).astype(str).str.strip())
    df.insert(1, "cidade", col("cidade").astype(str).str.strip().str.title())
    df["padrao_bairro"] = "medio"  # a lista não traz padrão do bairro
    df["ocupado"] = ocupado_padrao
    df["aceita_financiamento"] = (
        col("financiamento").astype(str).str.strip().str.lower().eq("sim").astype(int)
    )
    df["valor_avaliacao"] = _numero_br(col("avalia"))
    df["lance_minimo"] = _numero_br(col("preço").fillna(col("preco")))

    # colunas informativas extras (não usadas pelo modelo)
    df["uf"] = col("uf").astype(str).str.strip()
    df["bairro"] = col("bairro").astype(str).str.strip().str.title()
    df["endereco"] = col("endere").astype(str).str.strip()
    df["modalidade"] = col("modalidade").astype(str).str.strip()
    df["link"] = col("link").astype(str).str.strip()

    df = df.dropna(subset=["valor_avaliacao", "lance_minimo"])
    df = df[(df["valor_avaliacao"] > 0) & (df["lance_minimo"] > 0)]

    from .zonas import marcar_zona_leste
    return marcar_zona_leste(df.reset_index(drop=True))
