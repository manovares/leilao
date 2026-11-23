---
name: lupa-leiloes
description: Investigação profunda ("lupa") de lotes de leilão de imóveis já triados no site leilao-alpha.vercel.app. Use quando o Matheus mandar lotes favoritos, IDs, links ou a planilha do site e pedir para investigar, conferir, validar ou "passar a lupa" antes de dar lance. Não é para triagem em massa — isso o site já faz.
---

# Lupa de Leilões — dossiê do lote finalista

O site do Matheus (leilao-alpha.vercel.app) faz a triagem em massa: lê a planilha
(Caixa ou Arrematador), calcula o deságio efetivo e classifica os lotes em
A/B/C/D. Esta skill é a etapa seguinte: investigar A FUNDO os 1 a 5 melhores
lotes antes do lance. Triagem não é parecer — a lupa chega o mais perto possível
de um.

## Entrada

Aceite qualquer um destes formatos:
- Lista de lotes com dados (ID, endereço, bairro, cidade, tipo, m², quartos,
  vagas, avaliação, lance mínimo, modalidade, link do anúncio);
- Só IDs ou links de anúncio (Caixa, Zuk, Mega Leilões, Superbid etc.);
- A planilha original (CSV/Excel) + quais IDs investigar.

Se vierem mais de 5 lotes, pergunte quais priorizar (ou pegue os 5 de maior
deságio efetivo, avisando). Se faltar o essencial (endereço ou link), peça.

## Investigação por lote — nesta ordem

### 1. O anúncio e o edital
Abra o link do anúncio. Anote: modalidade exata (1º/2º leilão SFI, venda
online/direta, judicial 1ª/2ª praça), data, ocupação declarada, número da
matrícula e cartório, débitos citados (condomínio, IPTU), forma de pagamento
(à vista, financiamento, FGTS, parcelamento) e quem paga quais despesas.
Se o edital estiver linkado, leia as cláusulas de débitos e desocupação.

### 2. Valor de mercado — hierarquia de fontes
Use a melhor fonte disponível e ETIQUETE cada valor:
1. **[OFICIAL]** Transações reais de ITBI por distrito/endereço — em São Paulo
   capital, itbisp.com ou as guias de ITBI da Prefeitura (R$/m² pago de verdade);
2. **[CALCULADO]** Mediana de 10+ anúncios ativos do MESMO condomínio ou rua,
   mesmo perfil (tipo, área ±20%, quartos, vagas), em VivaReal, ZAP,
   QuintoAndar, Chaves na Mão, Imovelweb, OLX — SEMPRE excluindo anúncios de
   leilão, arremate ou venda judicial;
3. **[ESTIMADO]** Mediana do bairro/distrito com menos amostra, dizendo o
   tamanho da amostra.
Nunca use a avaliação do banco como valor de mercado — ela é o teto, não a
referência. Se anúncio mediano for a fonte, aplique ~7% de desconto de
negociação.

### 3. Conta completa (mesmos parâmetros do site)
- CTA = lance + comissão do leiloeiro 5% (NÃO existe em Venda Online/Direta da
  Caixa) + ITBI 3% (SP capital) + registro/escritura 1,5% + jurídico R$ 5.000 +
  desocupação (se ocupado ou sem informação) + reforma + condomínio/IPTU do
  período de posse + débitos que o edital deixar com o comprador;
- **Deságio efetivo** = 1 − CTA ÷ valor de mercado;
- Classe: A ≥ 30% · B 20–30% · C 10–20% · D < 10%; risco jurídico alto trava em C;
- **Lance máximo** p/ deságio-alvo de 20% =
  (mercado × 0,80 − custos fixos) ÷ (1 + comissão + ITBI + registro);
- Margem de revenda = (mercado × 0,94 − CTA) ÷ CTA (corretagem 6%), e IR de 15%
  sobre o ganho.

### 4. Riscos jurídicos — verificar um a um
- **Preço vil**: lance < 50% da avaliação em leilão JUDICIAL → risco de anulação
  (CPC, art. 891). Em leilão SFI (extrajudicial, Lei 9.514/1997) a regra não se
  aplica: o mínimo do 2º leilão é a dívida — que às vezes SUPERA a avaliação;
- **"Direitos sobre" / fração ideal / sem matrícula / usufruto**: o arrematante
  não leva a propriedade plena — risco alto, só com assessoria jurídica;
- **Débitos**: IPTU se sub-roga no valor do arremate em judicial (CTN,
  art. 130, § ún.); condomínio e IPTU ficam com o comprador na maioria dos
  lotes Caixa — pedir posição à administradora e certidão municipal;
- **Ocupação**: Caixa não informa na página; em SFI a regra é estar ocupado.
  Desocupação amigável/judicial leva 6–12 meses;
- **Parcelamento judicial**: 25% de entrada + até 30 meses (CPC, art. 895).

### 5. Checagem cruzada
Procure o MESMO imóvel em outros leiloeiros/agregadores (Zuk, Mega, Superbid,
Sodré Santoro, Leilão Imóvel) — preços ou datas diferentes para o mesmo lote são
sinal de edital novo. Veja se o condomínio aparece em notícias (inadimplência,
interdição, obra).

## Saída — dossiê por lote

Para cada lote, nesta estrutura, com toda afirmação etiquetada
[OFICIAL]/[CALCULADO]/[ESTIMADO]/[N/D]:

1. **Ficha**: endereço, tipo, m², modalidade, data do leilão, ocupação;
2. **Mercado**: valor adotado, fonte, amostra;
3. **Conta**: lance mínimo → CTA → deságio efetivo → classe → lance máximo →
   margem de revenda;
4. **Riscos**: lista do que foi confirmado, do que segue pendente e onde
   confirmar (edital, matrícula, administradora, certidões);
5. **Veredito**: "vale lance até R$ X", "só com desconto maior", ou "evitar —
   motivo", mais o checklist do que resolver ANTES do leilão.

Termine comparando os lotes investigados entre si e dizendo qual priorizar.
Lembre sempre: isto é análise prévia, não substitui a leitura do edital e da
matrícula nem assessoria jurídica para o arremate.
