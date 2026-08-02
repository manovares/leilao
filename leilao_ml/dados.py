"""Carregamento, validação e geração de dados de imóveis de leilão.

Esquema esperado do CSV de entrada (imóveis a analisar):

    id                   identificador do lote
    cidade               nome da cidade
    padrao_bairro        "alto", "medio" ou "baixo"
    tipo                 "apartamento", "casa", "terreno" ou "comercial"
    area_m2              área privativa/terreno em m²
    quartos              nº de quartos (0 para terreno/comercial)
    vagas                nº de vagas de garagem
    ocupado              1 se o imóvel está ocupado, 0 se desocupado
    aceita_financiamento 1 se aceita financiamento, 0 se só à vista
    valor_avaliacao      valor de avaliação do edital (R$)
    lance_minimo         lance mínimo do leilão (R$)

Para TREINAR com dados reais, o CSV precisa ter também as colunas de
resultado de operações passadas:

    preco_venda_real     preço pelo qual o imóvel foi revendido (R$)
    dias_ate_venda       dias entre a posse e a venda
"""

import numpy as np
import pandas as pd

COLUNAS_ENTRADA = [
    "id", "cidade", "padrao_bairro", "tipo", "area_m2", "quartos", "vagas",
    "ocupado", "aceita_financiamento", "valor_avaliacao", "lance_minimo",
]
COLUNAS_TREINO = COLUNAS_ENTRADA + ["preco_venda_real", "dias_ate_venda"]

# preço base por m² e índice de liquidez (1.0 = mercado muito líquido)
CIDADES = {
    "Sao Paulo":     (9_500, 1.00),
    "Rio de Janeiro": (8_500, 0.90),
    "Belo Horizonte": (6_500, 0.85),
    "Curitiba":      (6_800, 0.85),
    "Campinas":      (6_000, 0.85),
    "Porto Alegre":  (6_200, 0.80),
    "Salvador":      (5_200, 0.70),
    "Goiania":       (4_800, 0.75),
}
FATOR_BAIRRO = {"alto": 1.5, "medio": 1.0, "baixo": 0.7}
FATOR_TIPO = {"apartamento": 1.00, "casa": 0.95, "comercial": 0.90, "terreno": 0.55}
# terrenos e comerciais giram mais devagar que residenciais
FATOR_TEMPO_TIPO = {"apartamento": 1.0, "casa": 1.1, "comercial": 1.5, "terreno": 1.8}


def carregar_csv(caminho: str, treino: bool = False) -> pd.DataFrame:
    """Lê um CSV de imóveis e valida as colunas obrigatórias."""
    df = pd.read_csv(caminho)
    obrigatorias = COLUNAS_TREINO if treino else COLUNAS_ENTRADA
    faltando = [c for c in obrigatorias if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes no CSV: {faltando}")
    df = df.dropna(subset=[c for c in obrigatorias if c != "id"]).copy()
    df["cidade"] = df["cidade"].astype(str).str.strip()
    df["padrao_bairro"] = df["padrao_bairro"].str.lower().str.strip()
    df["tipo"] = df["tipo"].str.lower().str.strip()
    return df


def carregar_qualquer(caminho: str, treino: bool = False) -> pd.DataFrame:
    """Carrega um CSV no esquema do pipeline OU a lista oficial da Caixa,
    detectando o formato automaticamente."""
    from .arrematador import carregar_arrematador, eh_planilha_arrematador
    from .caixa import carregar_caixa, eh_planilha_caixa

    if eh_planilha_arrematador(caminho) or eh_planilha_caixa(caminho):
        if treino:
            raise ValueError(
                "Listas de leilão (Caixa/Arrematador) não têm resultado de "
                "operações passadas (preco_venda_real / dias_ate_venda) "
                "e não servem para treino."
            )
        if eh_planilha_arrematador(caminho):
            return carregar_arrematador(caminho)
        return carregar_caixa(caminho)
    return carregar_csv(caminho, treino=treino)


def gerar_dados_sinteticos(n: int = 4000, seed: int = 42) -> pd.DataFrame:
    """Gera um histórico sintético de operações para demonstração.

    Substitua por dados reais assim que tiver um histórico de
    arrematações e revendas — a qualidade do modelo depende disso.
    """
    rng = np.random.default_rng(seed)
    cidades = rng.choice(list(CIDADES), size=n)
    padroes = rng.choice(list(FATOR_BAIRRO), size=n, p=[0.2, 0.5, 0.3])
    tipos = rng.choice(list(FATOR_TIPO), size=n, p=[0.5, 0.3, 0.1, 0.1])

    area = np.where(
        np.isin(tipos, ["terreno"]),
        rng.uniform(125, 600, n),
        rng.lognormal(np.log(70), 0.4, n).clip(25, 400),
    ).round(0)
    quartos = np.where(
        np.isin(tipos, ["terreno", "comercial"]), 0,
        np.clip((area / 35).round() + rng.integers(-1, 2, n), 1, 5),
    ).astype(int)
    vagas = np.where(
        np.isin(tipos, ["terreno"]), 0,
        np.clip((area / 60).round() + rng.integers(-1, 2, n), 0, 4),
    ).astype(int)
    ocupado = rng.random(n) < 0.45
    aceita_fin = rng.random(n) < 0.4

    preco_m2 = np.array([CIDADES[c][0] for c in cidades])
    liquidez = np.array([CIDADES[c][1] for c in cidades])
    f_bairro = np.array([FATOR_BAIRRO[p] for p in padroes])
    f_tipo = np.array([FATOR_TIPO[t] for t in tipos])

    valor_mercado = (
        area * preco_m2 * f_bairro * f_tipo
        * (1 + 0.03 * quartos + 0.04 * vagas)
        * rng.uniform(0.85, 1.15, n)
    )
    valor_avaliacao = valor_mercado * rng.uniform(0.88, 1.10, n)
    desconto = rng.uniform(0.05, 0.60, n)
    lance_minimo = valor_avaliacao * (1 - desconto)

    # resultado da operação: revenda perto do valor de mercado pós-reforma
    preco_venda_real = valor_mercado * rng.uniform(0.93, 1.04, n)

    # tempo de venda: piora com baixa liquidez, preço acima do mercado,
    # tipo de imóvel e ausência de financiamento
    razao_preco = preco_venda_real / valor_mercado
    f_tempo_tipo = np.array([FATOR_TEMPO_TIPO[t] for t in tipos])
    dias_base = (
        75 / liquidez * f_tempo_tipo * razao_preco ** 4
        * np.where(aceita_fin, 0.85, 1.0)
    )
    dias_ate_venda = (dias_base * rng.lognormal(0, 0.35, n)).clip(15, 720).round(0)

    return pd.DataFrame({
        "id": [f"L{i:05d}" for i in range(1, n + 1)],
        "cidade": cidades,
        "padrao_bairro": padroes,
        "tipo": tipos,
        "area_m2": area,
        "quartos": quartos,
        "vagas": vagas,
        "ocupado": ocupado.astype(int),
        "aceita_financiamento": aceita_fin.astype(int),
        "valor_avaliacao": valor_avaliacao.round(0),
        "lance_minimo": lance_minimo.round(0),
        "preco_venda_real": preco_venda_real.round(0),
        "dias_ate_venda": dias_ate_venda,
    })
