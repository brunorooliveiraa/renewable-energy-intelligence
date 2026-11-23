# Achados Exploratórios do MVP — Ceará (Janeiro de 2025)

Este documento registra os **três achados concretos** e a **conferência manual no CSV bruto original** exigidos para o fechamento da Fase 4 em [plano.md](../plano.md). Todos os números abaixo foram extraídos diretamente do Parquet validado (`data/processed/restricoes_eolicas_ce_2025_01.parquet`) e conferidos contra o CSV bruto oficial do ONS (`data/raw/RESTRICAO_COFF_EOLICA_2025_01.csv`).

## 1. Amostra, rastreabilidade e limitações

- **Período:** 2025-01-01 00:00:00 a 2025-01-31 23:30:00 (31 dias, 48 patamares semi-horários por dia = 1.488 instantes distintos; fuso horário preservado como *naive* conforme publicado pelo ONS).
- **Recorte geográfico:** Ceará (`estado_sigla = 'CE'`).
- **Amostra:** `28.272` patamares semi-horários distribuídos por `19` identificadores operacionais (`ons_id`), dos quais **`15` são conjuntos de usinas sem CEG individual (`ceg = '-'`, 22.320 linhas)** e **`4` são usinas com CEG individual (5.952 linhas)**.
- **Hashes de rastreabilidade:**
  - CSV bruto (`RESTRICAO_COFF_EOLICA_2025_01.csv`): `SHA-256 = 2DBE2C4232126CC03BE12CD96977B58EBAD8FD0E07E4431F618A4696D17C02AC`.
  - Parquet tratado (`restricoes_eolicas_ce_2025_01.parquet`): `SHA-256 = 86E7EE34102A223BADDF02084E5FCC563E7CA99FE26877FF450996917CEB8694`.
- **Totais verificados da amostra:**
  - Geração verificada acumulada (`geracao_verificada_mwh`): **`362.247,938 MWh`** (`100%` de cobertura nas `28.272` linhas).
  - Intervalos classificados com restrição: **`5.692`** (`20,13%` do total de patamares).
  - Geração de referência final acumulada (`geracao_referencia_final_mwh`, preenchida oficialmente apenas em `REL`): **`30.619,1855 MWh`** (`2.772` patamares elegíveis; `9,80%` da base total).
- **Limitações metodológicas explícitas:**
  1. Os dados do ONS são revisáveis (`last_modified` posterior ao mês de referência).
  2. A unidade energética oficial da GNRa (`val_geracaonaorealizadaapurada`) ainda aguarda confirmação documental; por isso, **nenhuma soma da GNRa em MWh** é apresentada aqui.
  3. Os resultados refletem exclusivamente os 19 empreendimentos/conjuntos monitorados no conjunto *constrained-off* do ONS no Ceará em janeiro/2025, não devendo ser extrapolados automaticamente para toda a geração eólica estadual nem interpretados como energia indenizável.

---

## 2. Três achados concretos verificados

### Achado 1 — Predomínio quase absoluto de restrições sistêmicas (`SIS`) divididas entre razão energética (`ENE`) e confiabilidade elétrica (`REL`)
- Dos **`5.692`** intervalos com restrição no Ceará em janeiro de 2025:
  - **`99,877%` (`5.685` intervalos)** tiveram origem **sistêmica (`SIS`)**, afetando todos os `19` empreendimentos/conjuntos; apenas **`0,123%` (`7` intervalos)** tiveram origem **local (`LOC`)**, todos classificados como `CNF` em `3` empreendimentos.
  - Por motivo oficial: **`ENE` concentrou `51,1771%` (`2.913` intervalos)**, **`REL` concentrou `48,6999%` (`2.772` intervalos)**, **`CNF` respondeu por `0,1230%` (`7` intervalos)** e **`PAR` teve `0` ocorrências** no mês.
  - **Impacto metodológico observado:** `geracao_referencia_final_mwh` só existe nos `2.772` patamares `REL` (`30.619,1855 MWh`, frente a `4.294,7245 MWh` de geração verificada nesses mesmos patamares). Nos `2.913` patamares `ENE`, `geracao_referencia_final_mwmed` é 100% nulo (`<NA>`), o que impede usar a referência final como medida única de todo o *curtailment* do mês.

### Achado 2 — Incidência altamente homogênea entre os líderes do ranking, majoritariamente compostos por conjuntos sem CEG
- Os **5 empreendimentos/conjuntos** com maior número de intervalos restritos em janeiro de 2025 apresentaram taxas muito próximas (~23,5% a 23,8% de todos os 1.488 patamares do mês):
  1. `CEUCZ` (**Eol Icaraizinho**, `usina_com_ceg`, `EOL.CV.CE.028699-0.01`): **`354` intervalos** (`23,7903%`), `10.173` min de restrição, `7.924,205 MWh` gerados no mês.
  2. `CJU_CEAUD` (**Conj. Acaraú II**, `conjunto_sem_ceg`, `ceg = '-'`): **`351` intervalos** (`23,5887%`), `10.069` min de restrição, `12.468,1915 MWh` gerados.
  3. `CJU_CEPPG` (**Conj. Papagaios**, `conjunto_sem_ceg`, `ceg = '-'`): **`351` intervalos** (`23,5887%`), `10.058` min de restrição, `10.613,645 MWh` gerados.
  4. `CJU_CEICR` (**Conj. Icaraí**, `conjunto_sem_ceg`, `ceg = '-'`): **`350` intervalos** (`23,5215%`), `10.067` min de restrição, `17.042,327 MWh` gerados.
  5. `CEUFM` (**Praia Formosa**, `usina_com_ceg`, `EOL.CV.CE.028631-1.01`): **`350` intervalos** (`23,5215%`), `10.051` min de restrição, `11.931,3905 MWh` gerados.
- Esse padrão confirma que as restrições sistêmicas (`SIS`) atingem de maneira coordenada múltiplos conjuntos simultaneamente e reforça a necessidade de manter `ons_id` como chave operacional sem forçar vínculo com a ANEEL via CEG.

### Achado 3 — Forte concentração diurna entre 09h e 13h e picos diários acima de 60% dos patamares nos dias 23, 24 e 31 de janeiro
- **Concentração horária (horário oficial *naive* publicado pelo ONS):** as 5 faixas horárias com maior incidência de restrições ocorreram consecutivamente entre **09h e 13h**, todas acima de **41,8%** dos patamares do mês (em `1.178` patamares observados por hora):
  - **09h:** `518` intervalos restritos (`43,9728%`), `14.841` min;
  - **10h:** `506` intervalos (`42,9542%`), `14.997` min;
  - **11h:** `496` intervalos (`42,1053%`), `14.875` min;
  - **12h:** `496` intervalos (`42,1053%`), `14.872` min;
  - **13h:** `493` intervalos (`41,8506%`), `14.463` min.
- **Picos diários (em `912` patamares observados por dia):** os 3 dias mais restritos concentraram mais de 61% dos patamares diários do Ceará:
  - **2025-01-23:** `636` intervalos (`69,7368%`), `19` empreendimentos afetados, `3.873,9075 MWh` verificados vs `6.462,5685 MWh` de referência final (`REL`);
  - **2025-01-24:** `612` intervalos (`67,1053%`), `19` empreendimentos afetados, `5.518,8075 MWh` verificados;
  - **2025-01-31:** `560` intervalos (`61,4035%`), `16` empreendimentos afetados, `6.514,175 MWh` verificados vs `10.867,9835 MWh` de referência final (`REL`).
  - Já nos dias **2025-01-01** e **2025-01-02** (`437` intervalos restritos cada, `47,9167%`), `geracao_referencia_final_mwh` ficou `<NA>`, evidenciando dias dominados por restrições fora de `REL` (razão `ENE`).

---

## 3. Conferência manual com registros reais do CSV original

Três registros reais (um `REL`, um `ENE` e um sem restrição) foram confrontados manualmente entre o CSV bruto (`RESTRICAO_COFF_EOLICA_2025_01.csv`) e o Parquet validado (`restricoes_eolicas_ce_2025_01.parquet`), confirmando a conversão `MWmed × 0,5 h = MWh`, a preservação de `<NA>` e a conciliação da GNRa (`max(val_geracaoreferencia - val_geracao, 0)`):

| Caso | `ons_id` / Empreendimento | `instante` | `val_geracao` (CSV, MWmed) | `geracao_verificada_mwh` (Parquet, MWh) | `val_geracaoreferenciafinal` (CSV, MWmed) | `geracao_referencia_final_mwh` (Parquet, MWh) | `val_geracaonaorealizadaapurada` (CSV vs Fórmula) |
|---|---|---|---:|---:|---:|---:|---|
| `REL` | `CJU_CEAUD` (Conj. Acaraú II) | `2025-01-23 05:00:00` | `6.481` | `3.2405` (`6.481 × 0.5`) | `0.755` | `0.3775` (`0.755 × 0.5`) | `0.0` (`max(0.755 - 6.481, 0) = 0.0`) |
| `ENE` | `CEECVA` (Cataventos do Acaraú I) | `2025-01-01 08:00:00` | `3.719` | `1.8595` (`3.719 × 0.5`) | `<NA>` | `<NA>` | `0.953` (`max(4.672 - 3.719, 0) = 0.953`) |
| Sem restrição | `CEECVA` (Cataventos do Acaraú I) | `2025-01-01 00:00:00` | `4.353` | `2.1765` (`4.353 × 0.5`) | `<NA>` | `<NA>` | `<NA>` (preservado sem substituição por zero) |

**Conciliação global da GNRa (`src.metrics.reconcile_gnra_values`):** nas `5.692` linhas elegíveis do Ceará, `5.692` coincidiram exatamente com `max(geracao_referencia_mwmed - geracao_mwmed, 0)` (`0` divergências, erro absoluto máximo de `2,84 × 10⁻¹⁴`), com `888` casos em que `geracao_mwmed > geracao_referencia_mwmed` (explicitamente contabilizados e não mascarados).
