"""Cálculo do custo total de uma operação de leilão, da arrematação à venda."""

import numpy as np
import pandas as pd

from .config import ConfigCustos


def calcular_operacao(df: pd.DataFrame, preco_venda: np.ndarray,
                      meses_ate_venda: np.ndarray,
                      cfg: ConfigCustos) -> pd.DataFrame:
    """Calcula custos, investimento e lucro de cada imóvel.

    Considera o lance mínimo como preço de arrematação (cenário base);
    qualquer lance acima disso reduz o lucro na mesma proporção.
    Sobre o lance sempre incidem os custos extras de `cfg.custos_extras`
    (15% por padrão: possível reforma + ITBI + comissão do leiloeiro).
    """
    lance = df["lance_minimo"].to_numpy(float)
    ocupado = df["ocupado"].to_numpy(int)

    # Venda Online / Venda Direta não têm leiloeiro: desconta a comissão dos extras
    extras_pct = np.full(len(df), cfg.custos_extras)
    if "modalidade" in df.columns:
        mod = df["modalidade"].astype(str).str.lower()
        sem_leiloeiro = mod.str.contains("venda online") | mod.str.contains("venda direta")
        extras_pct = np.where(
            sem_leiloeiro, cfg.custos_extras - cfg.comissao_leiloeiro, cfg.custos_extras
        )
    custo_extras = lance * extras_pct
    custo_aquisicao = (
        lance * (1 + cfg.registro_cartorio)
        + custo_extras
        + cfg.custo_juridico_fixo
        + ocupado * cfg.custo_desocupacao
    )
    custo_posse = preco_venda * cfg.custo_mensal_posse * meses_ate_venda

    investimento_total = custo_aquisicao + custo_posse
    corretagem = preco_venda * cfg.corretagem_venda
    lucro_bruto = preco_venda - corretagem - investimento_total
    ir = np.clip(lucro_bruto, 0, None) * cfg.ir_ganho_capital
    lucro_liquido = lucro_bruto - ir

    return pd.DataFrame({
        "custo_aquisicao": custo_aquisicao.round(0),
        "custo_extras": custo_extras.round(0),
        "custo_posse": custo_posse.round(0),
        "investimento_total": investimento_total.round(0),
        "corretagem": corretagem.round(0),
        "ir_ganho_capital": ir.round(0),
        "lucro_liquido": lucro_liquido.round(0),
    }, index=df.index)
