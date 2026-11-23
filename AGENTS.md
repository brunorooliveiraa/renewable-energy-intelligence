# Regras para agentes

Estas regras valem para todo o repositório.

## Princípios obrigatórios

1. Nunca invente dados, resultados, fontes, URLs, colunas, unidades, métricas ou conclusões. Use somente evidências verificadas nos arquivos do projeto ou nas fontes oficiais citadas.
2. Quando um fato necessário não estiver disponível ou não puder ser confirmado, declare a limitação com clareza e pergunte ao usuário antes de tomar uma decisão que altere metodologia, escopo ou interpretação.
3. Nunca use `pass`, `...`, retornos fictícios, valores estáticos ou exceções ignoradas para fazer uma função parecer implementada. Uma função adicionada deve funcionar de verdade, validar suas entradas e falhar com mensagem clara quando não puder concluir o trabalho.
4. Não silencie erros. Não use `except` genérico sem registrar contexto e relançar ou tratar explicitamente uma exceção conhecida.
5. Não substitua valores ausentes por zero sem uma regra metodológica documentada e aprovada. Preserve os dados brutos e torne qualquer transformação rastreável.
6. Não crie dados sintéticos fora de testes identificados como tais. Dados de teste nunca podem ser apresentados como dados reais do ONS ou da ANEEL.
7. Não declare uma fase, comando, teste ou funcionalidade como concluída sem executá-la e verificar o resultado.
8. Sempre consulte o grafo de conhecimento (`graphify` / `graphify-out/`) para compreender a arquitetura, relações entre arquivos e contexto do projeto, e atualize o `graphify` sempre que criar, modificar ou remover código ou documentação.

## Grafo de conhecimento (Graphify)

- Antes de responder a perguntas sobre a arquitetura, dependências internas ou fluxo do repositório, consulte o `graphify` (`graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.json` ou comandos `graphify query` / `graphify path` / `graphify explain`).
- Sempre que realizar alterações em arquivos de código, testes ou documentação, atualize o grafo (`graphify --update` ou pipeline do skill `graphify`) antes de encerrar a tarefa, garantindo que `graphify-out/` reflita o estado real do projeto.

## Dados e metodologia

- Preserve arquivos brutos; transformações devem gerar novas saídas.
- Registre fonte, URL, data da coleta, arquivo de origem e hash sempre que aplicável.
- Consulte o dicionário oficial antes de assumir significado, unidade, granularidade ou chave de qualquer campo.
- Trate `MWmed` como potência média. Converta para `MWh` somente com a duração do intervalo validada e documentada.
- Não trate automaticamente a diferença entre geração de referência e geração verificada como energia desperdiçada, indenizável ou *constrained-off* oficial.
- Não trate toda linha como usina individual: a fonte pode conter conjuntos de usinas.
- Não force vínculo com a ANEEL quando o CEG estiver ausente, inválido ou representar um conjunto.
- Não descarte duplicidades ou registros anômalos silenciosamente; gere evidência e documente a regra adotada.

## Implementação

- Mantenha caminhos relativos à raiz do projeto; nunca grave caminhos absolutos de uma máquina no código.
- Prefira funções pequenas, tipadas e testáveis, com nomes e mensagens de erro claros.
- Adicione ou atualize testes para cada regra de cálculo e correção de defeito.
- Não quebre interfaces existentes sem explicar a necessidade e atualizar documentação e testes.
- Não adicione dependências sem necessidade demonstrável e registro explícito em `requirements.txt` (dependências leves da API serverless FastAPI + PostgreSQL na Vercel) ou `requirements-etl.txt` (dependências do pipeline ETL, análise e testes).
- Mantenha a API serverless (`api/index.py`) estritamente leve: **nunca** importe `pandas` ou `pyarrow` dentro de `api/`, nem execute etapas de ETL dentro de rotas HTTP.
- Todas as mensagens de commit devem ser escritas em português e todo avanço deve ser enviado primeiro para a branch `teste` antes de abrir PR para a `main`.
- Antes de concluir uma alteração, execute os testes e verificações relevantes. Se algo não puder ser executado, informe exatamente o que faltou.

## Frontend, API e dashboards

- Construa a interface com HTML semântico, CSS responsivo e JavaScript, sem Streamlit.
- Nunca escreva métricas analíticas reais diretamente no HTML ou JavaScript. O frontend deve consumir somente resultados produzidos pelo pipeline validado e servidos pela API FastAPI (`/api/*`).
- Não permita acesso direto do navegador ao PostgreSQL. Toda consulta do frontend deve passar por endpoints explícitos em `api/index.py` usando `DATABASE_URL` (pooled) no lado do servidor.
- Diferencie visualmente carregamento, ausência de dados e erro; ausência de registro nunca deve aparecer como zero.
- Mantenha filtros utilizáveis por teclado, rótulos acessíveis e unidades visíveis em cartões, tabelas e gráficos.

## Quando perguntar

Pergunte ao usuário quando houver ambiguidade que possa mudar o resultado, especialmente sobre fonte de dados, fórmula, unidade, licença, ferramenta, regra de negócio ou ação destrutiva. Apresente o que já foi verificado e formule uma pergunta objetiva; não adivinhe.


# Protocolo Obrigatório de Implementação e Auto-Revisão

Para toda alteração de código, execute exatamente estas 3 etapas antes de finalizar:

## Etapa 1: Testes de Falha (Execução Real)
Antes de considerar a tarefa pronta, escreva e execute testes automatizados cobrindo:
- Entradas inválidas, nulas/vazias ou fora do tipo esperado.
- Exceções que podem ocorrer (banco de dados, rede, parsing, I/O) — garantindo que não existam blocos `try/except` vazios ou silenciosos.
- Pelo menos 1 caso de borda da regra de negócio implementada.
Regra: Rode os testes e o linter/analisador estático do projeto. Não finalize se houver qualquer falha.

## Etapa 2: Auto-Revisão no `git diff` (Rúbrica Fechada)
Analise exclusivamente o `git diff` gerado e verifique apenas estes 4 critérios:
1. **Erro Lógico:** Existe alguma condição, loop ou cálculo que produz resultado errado para entradas reais do projeto?
2. **Validação:** Alguma função confia em dados externos/de usuário sem validar?
3. **Exceções:** Algum erro pode quebrar a execução sem tratamento adequado ou ser engolido silenciosamente?
4. **Regressão:** A mudança quebra algum comportamento já existente?

## Etapa 3: Trava Anti-Lixo
- É PROIBIDO sugerir ou aplicar refatorações puramente estéticas, renomeações sem motivo ou proteções para cenários hipotéticos fora do escopo atual.
- Se encontrar um erro na Etapa 2, você precisa provar com um teste ou entrada concreta que o erro acontece antes de alterar o código.
- Limite máximo: **2 ciclos** de correção. Se passar nos testes e na rúbrica, pare imediatamente.