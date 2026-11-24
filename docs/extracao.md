# Investigação da API CKAN do ONS

## Escopo

Este documento registra somente o primeiro tópico da Fase 2: verificar se a API CKAN do Portal de Dados Abertos do ONS permite descobrir recursos por conjunto, mês e formato sem manter uma lista manual de URLs.

Consulta realizada em 2026-11-22. Como o catálogo do ONS é atualizado, as contagens representam o estado observado nessa data e não devem ser codificadas como constantes do pipeline.

## Endpoints validados

### Pesquisa de conjuntos

```text
GET https://dados.ons.org.br/api/3/action/package_search?q=restricao%20coff%20eolica
```

A consulta retornou `success = true` e seis conjuntos. Como a busca textual não é única, o pipeline não poderá escolher simplesmente o primeiro resultado. Para o escopo atual, o identificador exato validado é:

```text
restricao_coff_eolica_usi
```

### Metadados e recursos do conjunto

```text
GET https://dados.ons.org.br/api/3/action/package_show?id=restricao_coff_eolica_usi
```

A resposta retornou `success = true`, o ID CKAN `bb70712b-4c9c-4495-88a9-8bcf4e9b6783` e 188 recursos:

- 186 recursos mensais;
- 62 períodos, de 2021-10 a 2026-11;
- 62 arquivos CSV;
- 62 arquivos Parquet;
- 62 arquivos XLSX;
- um dicionário PDF;
- um dicionário JSON.

Não havia duplicidade de período e formato na consulta.

## Janeiro de 2025

O nome CKAN comum aos três formatos é `Restricoes_coff_eolicas-2025-01`.

| Formato | ID do recurso CKAN | `last_modified` observado | URL oficial |
|---|---|---|---|
| Parquet | `2d53f755-c5be-4b90-bd87-c86250f4b196` | `2026-09-11T17:48:08.258245` | https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_tm/RESTRICAO_COFF_EOLICA_2025_01.parquet |
| CSV | `10f4c1a4-6fdc-4e4c-90ed-c6d8a1f285a9` | `2026-09-11T17:48:09.820139` | https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_tm/RESTRICAO_COFF_EOLICA_2025_01.csv |
| XLSX | `3a784999-0658-4795-aa72-e76a5eea4b61` | `2026-09-11T17:48:11.497573` | https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_tm/RESTRICAO_COFF_EOLICA_2025_01.xlsx |

A data `last_modified` é posterior ao mês de referência, confirmando que a descoberta deve preservar metadados de revisão e que um arquivo local não deve ser sobrescrito silenciosamente.

## Regra de descoberta recomendada

A função do próximo tópico deverá:

1. receber o identificador exato do conjunto, ano, mês e formato;
2. consultar `package_show` usando parâmetros HTTP, sem concatenar valores não validados à URL;
3. exigir `success = true` e a presença de `result.resources`;
4. reconhecer recursos mensais pelo padrão `Restricoes_coff_eolicas-AAAA-MM`;
5. comparar o formato sem diferenciar maiúsculas e minúsculas;
6. retornar exatamente um recurso com `id`, `name`, `format`, `url`, `created` e `last_modified`;
7. falhar claramente se não encontrar recurso ou se encontrar mais de um para o mesmo período e formato.

As contagens, o primeiro e o último mês disponíveis não serão fixados no código, pois mudam conforme novas publicações e revisões.

## Conclusão

A API CKAN atende ao primeiro requisito da Fase 2. Não é necessário manter URLs mensais manualmente. O próximo tópico pode implementar a função de descoberta sobre `package_show`, com seleção exata e validações explícitas.

## Função implementada

A função `src.extract.discover_resource` implementa a descoberta por identificador exato do conjunto, ano, mês e formato. Ela:

- valida todas as entradas antes da consulta;
- envia o identificador como parâmetro HTTP para `package_show`;
- aplica timeout configurável;
- exige uma resposta CKAN válida e bem-sucedida;
- aceita somente uma correspondência para período e formato;
- valida os campos obrigatórios e a URL retornada;
- não baixa nem altera arquivos.

Uma verificação integrada em 2026-11-22 retornou para `restricao_coff_eolica_usi`, janeiro de 2025 e CSV o recurso `10f4c1a4-6fdc-4e4c-90ed-c6d8a1f285a9`, consistente com a investigação manual registrada acima.

Os testes automatizados usam somente respostas sintéticas explicitamente identificadas e não dependem da disponibilidade da internet.

## Download seguro com tentativas e verificação de integridade

A função `src.extract.download_resource_file` implementa o download HTTP/HTTPS de um recurso descoberto com as seguintes garantias:

- valida todos os argumentos (`url`, `destination`, `timeout`, `max_attempts`, `chunk_size` e `overwrite`) antes de qualquer operação de disco ou rede;
- impede sobrescrita silenciosa quando o arquivo de destino já existe e `overwrite=False` (`FileExistsError`);
- realiza download em *streaming* (`stream=True`) para um arquivo temporário exclusivo (`.part`) no mesmo diretório do destino, calculando incrementalmente o tamanho em bytes e o hash `SHA-256`;
- repete a tentativa até `max_attempts` apenas em falhas transitórias (erros de conexão/timeout, interrupção de stream ou códigos HTTP `408`, `429`, `500`, `502`, `503`, `504`), falhando imediatamente em erros HTTP permanentes (como `404` ou `403`);
- verifica se o arquivo recebido não está vazio (`size_bytes > 0`) e se o tamanho coincide com `Content-Length` quando não há `Content-Encoding` ativo;
- promove atomicamente o arquivo `.part` para o destino final somente após todas as verificações e remove qualquer arquivo temporário em caso de erro.

## Padronização de nomes locais (`ons_eolica_YYYY_MM.csv`)

Para desacoplar o pipeline dos nomes variáveis dos recursos no S3/CKAN do ONS, `src.extract` define:

- `resolve_dataset_id(source_or_dataset)`: converte o identificador curto da fonte (`"eolica"`) ou o identificador do pacote CKAN (`"restricao_coff_eolica_usi"`) no par canônico `("eolica", "restricao_coff_eolica_usi")`;
- `build_raw_filename(source, year, month, file_format="csv")`: gera nomes determinísticos em minúsculas com ano de 4 dígitos e mês de 2 dígitos (`ons_eolica_2025_01.csv`);
- `build_raw_filepath(source, year, month, file_format="csv", output_dir=Path("data/raw"))`: resolve o caminho relativo padrão `data/raw/ons_eolica_YYYY_MM.csv` sem gravar caminhos absolutos da máquina;
- `download_monthly_resource(...)`: valida o destino antes da chamada de rede, descobre o recurso no CKAN e faz o download para o caminho previsível reutilizando a mesma sessão HTTP.

## Proteção contra sobrescrita silenciosa de revisões e manifesto de metadados

Para garantir rastreabilidade quando o ONS revisa arquivos históricos, `src.extract` vincula cada arquivo bruto a um manifesto sidecar `<arquivo>.metadata.json` (`ons_eolica_YYYY_MM.csv.metadata.json`):

- `compute_file_sha256(file_path)`: calcula o tamanho real em bytes e o hash `SHA-256` em *streaming* do arquivo em disco;
- `build_metadata_filepath(raw_filepath)`, `build_archived_revision_filepath(raw_filepath, sha256)`, `read_collection_metadata(metadata_path)` e `write_collection_metadata(metadata_path, metadata)`: leem, validam estritamente (ano de 4 dígitos, mês 1..12, `sha256` com 64 dígitos hexadecimais, `collected_at_utc` em ISO-8601 com fuso UTC explícito, `source_url` HTTP/HTTPS e correspondência `source`/`dataset`) e gravam atomicamente a estrutura `CollectionMetadata`;
- quando o arquivo local já existe e `overwrite=False`:
  - se o hash real em disco coincidir com o manifesto local **e** a versão remota no CKAN (`id`, `url` e `last_modified` não nulo) for idêntica, o arquivo local é reutilizado sem novo download (`attempts = 0`);
  - se não houver manifesto local, se o arquivo em disco tiver sido alterado ou se o CKAN apresentar uma revisão (mudança em `last_modified`, `id` ou `url`), `download_monthly_resource` lança `ResourceRevisionConflictError` sem sobrescrever o arquivo;
- quando `overwrite=True`:
  - o novo download é feito primeiro em um arquivo de *staging* e promovido em conjunto com o manifesto de forma transacional (`_commit_staged_raw_and_metadata`); se a escrita do manifesto falhar, o arquivo anterior é restaurado automaticamente (ou o arquivo novo é removido caso não existisse versão prévia), evitando qualquer inconsistência entre CSV e `.metadata.json`;
  - se o hash da nova revisão diferir do arquivo local anterior, a cópia física anterior é preservada em `ons_eolica_YYYY_MM.rev_<sha256[:12]>.csv` e adicionada à lista cumulativa `revision_history` do manifesto (além de atualizar `previous_sha256` e `previous_ckan_last_modified`).

## Faixa de meses, recursos ausentes e CLI (`python -m src.extract`)

- `iter_year_months(start_year, start_month, end_year, end_month)`: gera a sequência inclusiva de períodos `(ano, mês)`, suportando virada de ano e rejeitando faixas invertidas;
- `download_period_range(...)`: consulta o catálogo CKAN (`package_show`) **uma única vez** e pré-resolve todos os períodos solicitados em memória antes de iniciar qualquer download em disco, retornando uma lista ordenada de `MonthlyExtractionReport` com status explícito (`"downloaded"`, `"unchanged"` ou `"missing"`);
- períodos sem recurso compatível encontrado no catálogo CKAN para o conjunto, período e formato solicitados lançam `ResourceNotFoundError` por padrão (`allow_missing=False`) **antes** de baixar ou gravar qualquer arquivo, evitando efeitos parciais em disco; quando `allow_missing=True` (ou `--allow-missing` na CLI), apenas `ResourceNotFoundError` é registrado como `status="missing"`, sem nunca silenciar erros de rede, ambiguidade ou conflitos de revisão (`ResourceRevisionConflictError`);
- o módulo expõe o ponto de entrada CLI previsto no plano:
  - mês único: `python -m src.extract --year 2025 --month 1 --source eolica`
  - faixa de meses: `python -m src.extract --year 2025 --month 1 --end-month 3 --source eolica`
  - faixa entre anos tolerando períodos sem recurso compatível no formato solicitado: `python -m src.extract --year 2025 --month 11 --end-year 2026 --end-month 2 --source eolica --allow-missing`
