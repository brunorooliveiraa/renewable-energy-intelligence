# Dicionário e reconhecimento dos dados

## Fonte analisada

- Conjunto: restrições de operação por *constrained-off* de usinas eólicas.
- Instituição: Operador Nacional do Sistema Elétrico (ONS).
- Arquivo local: `data/raw/RESTRICAO_COFF_EOLICA_2025_01.csv`.
- Período observado: 2025-01-01 00:00:00 a 2025-01-31 23:30:00.
- Tamanho: 36.763.398 bytes.
- SHA-256: `2DBE2C4232126CC03BE12CD96977B58EBAD8FD0E07E4431F618A4696D17C02AC`.
- Formato confirmado: UTF-8, delimitador `;`, ponto como separador decimal.
- Dicionário consultado: JSON oficial vigente do ONS e PDF versão 1.4, datado de 2025-09-26.
- Página oficial do conjunto: https://dados.ons.org.br/dataset/restricao_coff_eolica_usi
- Dicionário JSON oficial: https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_tm/DicionarioDados_RestricaoContrainedoff_UsiEolicas.json
- Rotina operacional consultada como referência metodológica vigente: RO-AO.BR.13, revisão 08. A revisão entrou em vigor depois do mês analisado e não será tratada automaticamente como a norma aplicável a janeiro de 2025.
- Cópias locais preservadas: [`referencias/ons/DicionarioDados_RestricaoContrainedoff_UsiEolicas.pdf`](referencias/ons/DicionarioDados_RestricaoContrainedoff_UsiEolicas.pdf) e [`referencias/ons/DicionarioDados_RestricaoContrainedoff_UsiEolicas.json`](referencias/ons/DicionarioDados_RestricaoContrainedoff_UsiEolicas.json).

O portal do ONS informa que o conjunto passa por consistência recorrente e pode ser atualizado após a publicação. O hash acima identifica somente a cópia efetivamente analisada.

## Esquema observado

| Campo | Interpretação oficial resumida | Observação inicial |
|---|---|---|
| `id_subsistema` | Identificador do subsistema | Texto |
| `nom_subsistema` | Nome do subsistema | Texto |
| `id_estado` | Sigla da UF | `CE` no recorte do MVP |
| `nom_estado` | Nome do estado | Texto |
| `nom_usina` | Nome da usina ou conjunto | Não implica parque individual |
| `id_ons` | Identificador da usina ou conjunto no ONS | Chave operacional candidata |
| `ceg` | Código ANEEL; conjuntos usam `-` | Preservar como texto |
| `din_instante` | Data e hora do patamar | Intervalos observados de 30 minutos |
| `val_geracao` | Geração verificada, em MWmed | Não confundir com MWh |
| `val_geracaolimitada` | Limite estabelecido pelo ONS, em MWmed | Nulo significa que não houve limitação estabelecida no patamar |
| `val_disponibilidade` | Disponibilidade eletromecânica verificada, em MWmed | Numérico |
| `val_geracaoreferencia` | Estimativa sem limitação, em MWmed | Numérico |
| `val_geracaoreferenciafinal` | Referência final, em MWmed | Oficialmente calculada apenas em patamares `REL` |
| `cod_razaorestricao` | `REL`, `CNF`, `ENE` ou `PAR` | Nulo fora de restrição classificada |
| `cod_origemrestricao` | `LOC` ou `SIS` | Nulo fora de restrição classificada |
| `dsc_restricao` | Detalhamento do motivo | 100% nulo no recorte CE analisado |
| `id_pontoconexao` | Identificador do ponto de conexão | Texto |
| `nom_pontoconexao` | Nome do ponto de conexão | Texto |
| `nom_agenteoperador` | Agente responsável pela operação | Texto |
| `val_geracaonaorealizadaapurada` | Geração Não Realizada Apurada (GNRa) | Unidade ainda precisa ser confirmada antes da agregação |
| `num_minutos_rel` | Minutos com restrição `REL` no patamar | Entre 0 e 30 nas linhas preenchidas |
| `num_minutos_cnf` | Minutos com restrição `CNF` no patamar | Entre 0 e 30 nas linhas preenchidas |
| `num_minutos_ene` | Minutos com restrição `ENE` no patamar | Entre 0 e 30 nas linhas preenchidas |
| `num_minutos_restricao` | Minutos com qualquer restrição no patamar | Entre 1 e 30 nas linhas de restrição do Ceará |

## Diagnóstico do arquivo completo

- 232.128 linhas e 24 colunas.
- Nove estados presentes.
- Nenhuma data inválida.
- Nenhuma linha exatamente duplicada.
- Nenhuma duplicidade na chave candidata `id_ons + din_instante`.

## Contrato de leitura e nomes internos

`src.transform.read_raw_ons_csv` lê os arquivos brutos sem modificá-los usando
explicitamente UTF-8 (com ou sem BOM), delimitador `;` e separador decimal `.`.
Nesta primeira etapa estrutural, todos os valores permanecem como texto
anulável: somente campos vazios viram ausentes, `-` é preservado e datas/medidas
ainda não são convertidas. Como o pandas não aplica o argumento `decimal` a
colunas textuais, o leitor rejeita explicitamente vírgulas nos campos numéricos;
a conversão e a validação numérica completa continuam reservadas ao tópico
seguinte da Fase 3.

O cabeçalho deve conter exatamente as 24 colunas oficiais conhecidas e cada
registro deve possuir exatamente 24 campos. Campos ausentes, adicionais ou
duplicados, assim como linhas truncadas ou excedentes, interrompem o processo
com erro que identifica o registro, sem permitir preenchimento ou deslocamento
silencioso pelo pandas. Ponto e vírgula dentro de texto continua permitido
quando estiver corretamente protegido pelas regras do CSV.

O mapeamento reversível `SOURCE_TO_INTERNAL_COLUMNS` / `INTERNAL_TO_SOURCE_COLUMNS`
preserva o vínculo entre nomes oficiais e internos. Os principais grupos são:

| Nome oficial | Nome interno |
|---|---|
| `id_estado` / `nom_estado` | `estado_sigla` / `estado_nome` |
| `id_ons` / `nom_usina` | `ons_id` / `usina_nome` |
| `din_instante` | `instante` |
| `val_geracao` | `geracao_mwmed` |
| `val_geracaolimitada` | `geracao_limitada_mwmed` |
| `val_disponibilidade` | `disponibilidade_mwmed` |
| `val_geracaoreferencia` | `geracao_referencia_mwmed` |
| `val_geracaoreferenciafinal` | `geracao_referencia_final_mwmed` |
| `val_geracaonaorealizadaapurada` | `geracao_nao_realizada_apurada` |
| `num_minutos_restricao` | `minutos_restricao_total` |

O nome interno da GNRa não declara unidade porque ela continua pendente de
confirmação documental. O mapeamento integral das 24 colunas permanece no
código, é testado contra colisões e pode ser invertido sem perda de informação.

## Diagnóstico do Ceará

- 28.272 linhas.
- 19 valores distintos de `id_ons` e 19 nomes distintos.
- 1.488 instantes distintos, equivalentes aos 31 dias de janeiro multiplicados por 48 patamares semi-horários.
- Cada `id_ons` possui 1.488 linhas, de 00:00 de 1º de janeiro a 23:30 de 31 de janeiro.
- Todos os passos consecutivos observados por `id_ons` têm 30 minutos.
- Nenhuma duplicidade exata ou na chave candidata.
- Nenhum valor negativo nas colunas inferidas como numéricas.
- Quatro identificadores possuem CEG; 15 são conjuntos representados por `-`, totalizando 22.320 linhas sem CEG individual.

### Restrições observadas

| Razão | Origem | Linhas | Referência final preenchida | GNRa preenchida |
|---|---:|---:|---:|---:|
| `REL` | `SIS` | 2.772 | 2.772 | 2.772 |
| `ENE` | `SIS` | 2.913 | 0 | 2.913 |
| `CNF` | `LOC` | 7 | 0 | 7 |
| Sem código | Sem código | 22.580 | 0 | 0 |

Não há código `PAR` no recorte analisado. A ausência no mês não significa que esse domínio seja inválido.

## Decisões e pendências

1. Usar `id_ons + din_instante` como chave candidata na próxima fase, mantendo validação por arquivo antes de impor unicidade no banco.
2. Não vincular os 15 conjuntos à ANEEL por CEG.
3. Não substituir nulos por zero.
4. Não calcular energia a partir da GNRa até confirmar documentalmente sua unidade e a forma correta de considerar `num_minutos_restricao`.
5. Conciliar manualmente amostras de `val_geracaonaorealizadaapurada` com os campos de geração, referência e minutos antes de escolher o indicador principal do dashboard.
6. O PDF versão 1.4 não lista todos os campos presentes no CSV; o JSON oficial vigente lista as 24 colunas. Essa diferença deve ser considerada no versionamento do esquema.

## Conciliação inicial da GNRa

Nas 5.692 linhas do Ceará em que `val_geracaonaorealizadaapurada` está preenchida, o valor coincide com `max(val_geracaoreferencia - val_geracao, 0)` nas 5.692 observações, com erro absoluto máximo de `2,84 × 10⁻¹⁴`, compatível com precisão de ponto flutuante.

A multiplicação adicional por `num_minutos_restricao / 30` não reproduz 358 dessas observações. Portanto, os minutos não devem ser reaplicados para tentar reconstruir a GNRa publicada. Essa conciliação numérica não resolve, por si só, a unidade energética do campo nem autoriza sua soma como MWh.
