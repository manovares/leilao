"""Premissas de custo de uma operação de compra em leilão no Brasil.

Todos os percentuais são sobre o valor indicado no comentário.
Ajuste os valores para a realidade da sua cidade/operação, ou carregue
um JSON próprio com `ConfigCustos.de_json`.
"""

import json
from dataclasses import dataclass, asdict


@dataclass
class ConfigCustos:
    # --- custos de aquisição ---
    custos_extras: float = 0.15           # % sobre o lance: possível reforma + ITBI + leiloeiro
    comissao_leiloeiro: float = 0.05      # parcela dos extras dispensada em Venda Online/Direta (sem leiloeiro)
    registro_cartorio: float = 0.015      # % sobre o lance
    custo_juridico_fixo: float = 5_000.0  # assessoria jurídica / due diligence (R$)
    custo_desocupacao: float = 15_000.0   # ação de imissão na posse, se ocupado (R$)

    # --- custos até a venda ---
    custo_mensal_posse: float = 0.0015    # % do valor de mercado por mês (IPTU + condomínio)

    # --- custos na venda ---
    corretagem_venda: float = 0.06        # % sobre o preço de venda
    ir_ganho_capital: float = 0.15        # % sobre o lucro (pessoa física)

    def para_json(self, caminho: str) -> None:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def de_json(cls, caminho: str) -> "ConfigCustos":
        with open(caminho, encoding="utf-8") as f:
            return cls(**json.load(f))
