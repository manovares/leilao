# Leilão ML — análise de oportunidades em imóveis de leilão

Pipeline de machine learning que analisa uma base de imóveis de leilão e, para cada lote:

1. **Prevê o preço de venda** (revenda pós-reforma) com um modelo de gradient boosting;
2. **Prevê o tempo até vender** em três cenários — otimista (P25), esperado (P50) e conservador (P90) — usando regressão de quantis;
3. **Calcula o custo total da operação**: arrematação, comissão do leiloeiro, ITBI, cartório, jurídico, desocupação (se ocupado), reforma, custo de posse (IPTU/condomínio durante o período de venda), corretagem e IR sobre ganho de capital;
4. **Ranqueia as melhores oportunidades** por retorno mensalizado (ROI ajustado pelo tempo de venda no cenário conservador), com score de 0 a 100 e classificação (`excelente / boa / regular / evitar`).

## Como usar

```bash
pip install -r requirements.txt

# 1. Treinar os modelos (usa dados sintéticos de demonstração se você não passar --dados)
python treinar.py

# 2. Analisar um edital/lista de leilão
python analisar.py --dados data/exemplo_leilao.csv --top 15
```

A saída é impressa no terminal e o ranking completo é salvo em `resultado_oportunidades.csv`.

## Usando seus próprios dados

### Imóveis a analisar (`analisar.py --dados seu_edital.csv`)

CSV com as colunas:

| coluna | descrição |
|---|---|
| `id` | identificador do lote |
| `cidade` | cidade do imóvel |
| `padrao_bairro` | `alto`, `medio` ou `baixo` |
| `tipo` | `apartamento`, `casa`, `terreno` ou `comercial` |
| `area_m2` | área em m² |
| `quartos`, `vagas` | quartos e vagas (0 se não se aplica) |
| `ocupado` | 1 se ocupado, 0 se desocupado |
| `aceita_financiamento` | 1 se aceita financiamento/FGTS |
| `valor_avaliacao` | valor de avaliação do edital (R$) |
| `lance_minimo` | lance mínimo (R$) |

### Histórico real para treinar (`treinar.py --dados historico.csv`)

Mesmas colunas acima **mais** o resultado de operações passadas:

| coluna | descrição |
|---|---|
| `preco_venda_real` | preço pelo qual o imóvel foi revendido (R$) |
| `dias_ate_venda` | dias entre a posse e a venda |

> **Importante:** o repositório treina por padrão com dados **sintéticos** de demonstração, gerados em `leilao_ml/dados.py`. Eles servem para validar o pipeline, não para decidir investimento. Substitua pelo seu histórico real (ou por dados de mercado da sua região) assim que possível — a qualidade das previsões depende disso.

## Ajustando as premissas de custo

Os percentuais padrão estão em `leilao_ml/config.py` (leiloeiro 5%, ITBI 3%, cartório 1,5%, reforma R$ 400/m², desocupação R$ 15.000, corretagem 6%, IR 15% etc.). Para usar valores próprios:

```python
from leilao_ml.config import ConfigCustos
ConfigCustos(itbi=0.02, reforma_por_m2=600).para_json("custos.json")
```

```bash
python analisar.py --dados edital.csv --config custos.json
```

## Estrutura do projeto

```
leilao_ml/
├── config.py         # premissas de custo da operação
├── dados.py          # esquema do CSV, validação e gerador de dados sintéticos
├── modelos.py        # modelo de preço + modelos de quantil de tempo de venda
├── custos.py         # cálculo do investimento total e lucro líquido
└── oportunidades.py  # ranking, score e relatório
treinar.py            # CLI de treino
analisar.py           # CLI de análise/ranking
data/exemplo_leilao.csv  # exemplo de edital para testar
```

## Como o score é calculado

Para cada imóvel: `lucro líquido / investimento total = ROI`, convertido em **retorno mensal** usando o prazo de venda do cenário conservador (P90) — assim um imóvel muito lucrativo mas que pode demorar um ano para vender não fica acima de um imóvel com lucro menor e giro rápido. O score 0–100 é o percentil desse retorno dentro do lote analisado.

## Aviso

Este projeto é uma ferramenta de apoio à decisão, não uma recomendação de investimento. Leilões de imóveis envolvem riscos jurídicos (ocupação, dívidas, anulação) que não são capturados pelo modelo — sempre faça due diligence com apoio jurídico antes de dar um lance.
