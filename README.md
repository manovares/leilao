# Leilão ML — análise de oportunidades em imóveis de leilão

Pipeline de machine learning que analisa uma base de imóveis de leilão e, para cada lote:

1. **Prevê o preço de venda** (revenda pós-reforma) com um modelo de gradient boosting;
2. **Prevê o tempo até vender** em três cenários — otimista (P25), esperado (P50) e conservador (P90) — usando regressão de quantis;
3. **Calcula o custo total da operação**: sobre o lance sempre incidem **+15% de custos extras** (possível reforma + ITBI + comissão do leiloeiro), além de cartório, jurídico, desocupação (se ocupado), custo de posse (IPTU/condomínio durante o período de venda), corretagem e IR sobre ganho de capital;
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

### Lista de Imóveis da Caixa (formato oficial)

O CSV baixado de [venda-imoveis.caixa.gov.br](https://venda-imoveis.caixa.gov.br) funciona **sem nenhuma alteração**, tanto no front-end (upload) quanto nos scripts — o formato é detectado automaticamente (codificação ISO-8859-1, banner, separador `;`), e tipo, área, quartos, vagas e link do anúncio são extraídos do campo "Descrição":

```bash
python analisar.py --dados data/Lista_imoveis_SP.csv
python exportar_frontend.py --dados data/Lista_imoveis_SP.csv --top 1000
```

Como a lista não informa ocupação, o custo de desocupação é incluído por padrão (conservador).

### Planilha do Arrematador

A planilha exportada do Arrematador (colunas `ID IMOVEL`, `MODALIDADE`, `TIPO IMOVEL`, `ESTADO`, `CIDADE`, `VALOR AVALIAÇÃO`, `VALOR DE VENDA`, `ACEITA FINANCIAMENTO`, `ACEITA FGTS`, `DESCRICAO`, `DATA LEILÃO`, `LINK`) também é detectada automaticamente — salve como CSV e use nos scripts ou no upload do site. No front-end, cada formato abre na sua própria aba ("Planilha Arrematador" / "Lista Caixa"), e as duas podem ficar carregadas ao mesmo tempo.

### Outros formatos (`analisar.py --dados seu_edital.csv`)

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

Os percentuais padrão estão em `leilao_ml/config.py` (**custos extras +15% sobre o lance** — possível reforma + ITBI + leiloeiro —, cartório 1,5%, desocupação R$ 15.000, corretagem 6%, IR 15% etc.). Para usar valores próprios:

```python
from leilao_ml.config import ConfigCustos
ConfigCustos(custos_extras=0.18).para_json("custos.json")
```

```bash
python analisar.py --dados edital.csv --config custos.json
```

## Front-end (dashboard)

O dashboard em `frontend/` mostra os KPIs do lote, o top 10 por retorno mensal, o ranking completo (ordenável, com detalhamento de custos por imóvel) e um **simulador de arremate** que sempre aplica os +15% de custos extras. É 100% estático — basta abrir `frontend/index.html` no navegador.

Para atualizar os dados exibidos após uma nova análise:

```bash
python exportar_frontend.py --dados data/exemplo_leilao.csv
```

### Deploy na Vercel

O `vercel.json` já aponta a pasta `frontend/` como saída estática. Basta:

1. Acessar [vercel.com/new](https://vercel.com/new) e importar este repositório do GitHub; **ou**
2. Rodar `npx vercel --prod` na raiz do projeto (requer login na Vercel).

Nenhum build é necessário — a Vercel serve os arquivos estáticos diretamente.

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
