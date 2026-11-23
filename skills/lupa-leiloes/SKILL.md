---
name: lupa-leiloes
description: Leilões de imóveis em São Paulo para o Matheus, em dois modos. VARREDURA — quando ele pedir para buscar/procurar imóveis de leilão sem mandar lote nenhum ("busca aí", "o que tem de bom", "varre os sites"), vasculhar o portal da Caixa, os leiloeiros credenciados e os agregadores, sempre em SP. LUPA — quando ele mandar lotes, IDs, links ou favoritos do site leilao-alpha.vercel.app e pedir para investigar/validar antes do lance, montar o dossiê profundo de cada um.
---

# Lupa de Leilões — varredura e dossiê (São Paulo)

O site do Matheus (leilao-alpha.vercel.app) tria planilhas em massa. Esta skill
cobre o resto: **varrer os sites de leilão sem planilha** e **investigar a
fundo os finalistas**. Padrões fixos do Matheus: imóveis em **São Paulo**
(capital primeiro, com destaque para a **Zona Leste**; litoral e interior se
ele pedir), nunca precisar de link para começar, e toda afirmação etiquetada
[OFICIAL] / [CALCULADO] / [ESTIMADO] / [N/D].

## MODO VARREDURA — "busca aí pra mim"

Ative quando ele pedir para buscar/procurar imóveis sem fornecer lotes.
Se ele não disser faixa de preço, use **R$ 100 mil a R$ 500 mil** e avise que
dá para mudar. Se não disser região, use **São Paulo capital, Zona Leste em
destaque**.

Varra nesta ordem (busca na web + leitura das páginas de busca de cada site,
filtrando por São Paulo e pela faixa):

1. **Imóveis CAIXA** (venda-imoveis.caixa.gov.br) — maior oferta; anote
   modalidade (1º/2º leilão SFI, venda online/direta) e data;
2. **Leiloeiros que operam os leilões da Caixa e de bancos**: Zuk (portalzuk),
   Mega Leilões, Sodré Santoro, Superbid, Fidalgo, Frazão, Biasi, Lance no
   Leilão, Leilão VIP — os credenciados variam por edital, então cubra os que
   conseguir ler e diga quais ficaram de fora;
3. **Agregadores**: Leilão Imóvel (leilaoimovel.com.br), VipLeilões;
4. **Bancos e afins** se der tempo: Santander Imóveis, Bradesco, Itaú,
   Emgea/Resale, e leilões judiciais do TJSP.

Um site que bloquear a leitura não trava a varredura: registre "não acessível
nesta rodada" e siga. A varredura é triagem leve — uns 15 a 40 lotes lidos com
atenção por rodada; diga isso.

Para cada lote encontrado, estime rápido: valor de mercado da região
([ESTIMADO] por m² do distrito; ITBI se houver tempo), CTA aproximado (regras
abaixo) e **deságio efetivo**. Entregue um ranking com: endereço/bairro, tipo,
m², lance mínimo, modalidade, data, site + link, deságio efetivo estimado e
classe provisória. Termine oferecendo a LUPA nos 3–5 melhores.

## MODO LUPA — dossiê do finalista

Ative quando ele mandar lotes (dados, IDs, links ou favoritos do site).
Máximo 5 por vez; com mais, pegue os 5 de maior deságio efetivo e avise.

### 1. O anúncio e o edital
Abra o link. Anote: modalidade exata, data, ocupação declarada, matrícula e
cartório, débitos citados (condomínio, IPTU), formas de pagamento
(financiamento, FGTS, parcelamento) e quem paga quais despesas. Se o edital
estiver linkado, leia as cláusulas de débitos e desocupação.

### 2. Valor de mercado — hierarquia de fontes
1. **[OFICIAL]** Transações de ITBI por distrito/endereço — na capital,
   itbisp.com ou as guias de ITBI da Prefeitura (R$/m² pago de verdade);
2. **[CALCULADO]** Mediana de 10+ anúncios ativos do MESMO condomínio ou rua,
   mesmo perfil (tipo, área ±20%, quartos, vagas), em VivaReal, ZAP,
   QuintoAndar, Chaves na Mão, Imovelweb, OLX — SEMPRE excluindo anúncios de
   leilão, arremate ou venda judicial; com anúncio como fonte, desconte ~7%
   de negociação;
3. **[ESTIMADO]** Mediana do bairro/distrito, dizendo o tamanho da amostra.
Nunca use a avaliação do banco como valor de mercado — ela é teto, não
referência.

### 3. Conta completa (mesmos parâmetros do site)
- CTA = lance + comissão do leiloeiro 5% (NÃO existe em Venda Online/Direta
  da Caixa) + ITBI 3% (SP capital) + registro/escritura 1,5% + jurídico
  R$ 5.000 + desocupação (se ocupado ou sem informação) + reforma +
  condomínio/IPTU do período de posse + débitos que ficarem com o comprador;
- **Deságio efetivo** = 1 − CTA ÷ valor de mercado;
- Classe: A ≥ 30% · B 20–30% · C 10–20% · D < 10%; risco jurídico alto trava
  em C;
- **Lance máximo** p/ deságio-alvo de 20% =
  (mercado × 0,80 − custos fixos) ÷ (1 + comissão + ITBI + registro);
- Margem de revenda = (mercado × 0,94 − CTA) ÷ CTA (corretagem 6%) e IR de
  15% sobre o ganho.

### 4. Riscos jurídicos — um a um
- **Preço vil**: lance < 50% da avaliação em leilão JUDICIAL → risco de
  anulação (CPC, art. 891). Não vale para leilão SFI (Lei 9.514/1997), onde o
  mínimo do 2º leilão é a dívida — que às vezes SUPERA a avaliação;
- **"Direitos sobre" / fração ideal / sem matrícula / usufruto**: não é
  propriedade plena — risco alto, só com assessoria jurídica;
- **Débitos**: IPTU se sub-roga no arremate em judicial (CTN, art. 130,
  § ún.); condomínio e IPTU ficam com o comprador na maioria dos lotes Caixa —
  pedir posição à administradora e certidão municipal;
- **Ocupação**: a Caixa não informa na página; em SFI a regra é estar
  ocupado. Desocupação leva 6–12 meses;
- **Parcelamento judicial**: 25% de entrada + até 30 meses (CPC, art. 895).

### 5. Checagem cruzada
Procure o MESMO imóvel nos outros leiloeiros/agregadores — preço ou data
diferente é sinal de edital novo. Veja se o condomínio aparece em notícias.

### Saída do dossiê
Por lote: **Ficha** (endereço, tipo, m², modalidade, data, ocupação) →
**Mercado** (valor, fonte, amostra) → **Conta** (lance mínimo → CTA → deságio
efetivo → classe → lance máximo → margem) → **Riscos** (confirmados,
pendentes, onde confirmar) → **Veredito** ("vale lance até R$ X", "só com
desconto maior" ou "evitar — motivo") + checklist pré-leilão.

Termine comparando os lotes e dizendo qual priorizar. Sempre lembre: análise
prévia não substitui a leitura do edital e da matrícula nem assessoria
jurídica para o arremate.
