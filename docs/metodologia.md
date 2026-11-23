# Metodologia

A metodologia será preenchida com evidências durante as fases de reconhecimento e validação dos dados. As premissas propostas, ainda não validadas, estão registradas em `plano.md`.

Nenhum indicador analítico foi calculado nesta fase.

## Descoberta da Fase 1

O arquivo de janeiro de 2025 contém o campo oficial `val_geracaonaorealizadaapurada` (GNRa) e campos com minutos de restrição por razão. O dicionário JSON oficial descreve a GNRa como uma estimativa apurada nos períodos de limitação, mas a unidade desse campo ainda não foi confirmada na documentação consultada.

Até essa confirmação e uma conciliação manual de amostras, o projeto não somará a GNRa, não a converterá para MWh e não a substituirá pelo indicador exploratório originalmente proposto no plano.

A conciliação inicial de todas as 5.692 linhas preenchidas no recorte do Ceará confirmou que a GNRa publicada coincide numericamente com `max(val_geracaoreferencia - val_geracao, 0)`. Uma ponderação adicional pelos minutos de restrição não reproduz todos os registros e não será aplicada. A conversão ou agregação energética continua pendente da confirmação documental da unidade.

## Convenção de data/hora e tipagem numérica (Fase 3)

- **Fuso horário de `din_instante` (`instante`):** o ONS publica os patamares no formato exato `YYYY-MM-DD HH:MM:SS` sem sufixo de fuso horário. Como a documentação consultada ainda não formaliza um offset explícito no arquivo CSV, a função `src.transform.parse_instante_column` preserva a coluna como `datetime64[ns]` *timezone-naive* (política explícita `naive_ons_official_clock`), sem aplicar `tz_localize` nem deslocar horários silenciosamente. Datas fora do formato exato ou com sufixo inesperado (`Z`, `-03:00`) são rejeitadas explicitamente.
- **Tipagem das medidas em MWmed:** a função `src.transform.convert_mwmed_columns` converte apenas as 5 colunas com unidade `MWmed` confirmada no dicionário oficial (`geracao_mwmed`, `geracao_limitada_mwmed`, `disponibilidade_mwmed`, `geracao_referencia_mwmed` e `geracao_referencia_final_mwmed`) para `Float64` anulável (IEEE-754 de 64 bits), sem arredondamento precoce e sem substituir nulos por zero. Strings com vírgula decimal ou valores não finitos (`nan`, `inf`, `-inf`) são rejeitados explicitamente. A coluna `geracao_nao_realizada_apurada` permanece fora desse grupo até confirmação documental de sua unidade.
