## Passo 1 — Inventário de Acesso (Read-only)
- Criar rotina de descoberta que lista todas as tabelas e colunas disponíveis via `EXTERNAL_DB_URL`.
- Consultas genéricas:
  - Postgres: `SELECT table_schema, table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema');`
  - Colunas: `SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema');`
  - SQLite (se aplicável): `SELECT name FROM sqlite_master WHERE type='table';` e `PRAGMA table_info(<tabela>)`.
- Resultado: inventário JSON com `{tabela: [colunas...]}` para todas as tabelas a que temos acesso.

## Passo 2 — Mapeamento Automático
- Heurísticas para detectar campos do print:
  - `id_favorecido`→ colunas contendo `favorecido`, `id_fav`.
  - `chave_oamd/ZW`→ colunas contendo `chave`, `zw`, `infra`.
  - `cnpj`→ coluna contendo `cnpj`.
  - `data_cadastro`/`data_*`→ colunas de data próximas.
  - `url_integracao`→ colunas contendo `url`, `integracao`.
  - `nps`→ tabelas/colunas contendo `nps`/`pesquisa`.
  - `situacao/sincronizacao`→ colunas contendo `situacao`, `sincronizacao`.
  - Nome fantasia/razão/social/endereco→ colunas textuais com esses termos.
- Produzir um mapeamento candidato `{campo_print: {tabela, coluna}}` e permitir ajustes manuais via config.

## Passo 3 — Preview de Dados (Read-only)
- Endpoint `GET /api/v1/oamd/implantacoes/<impl_id>/preview_full` que:
  - Usa o mapeamento para consultar em cada tabela/coluna detectada, filtrando por chave local disponível (preferência: `id_favorecido`, fallback `cnpj`, `chave_oamd`).
  - Retorna `persistibles` (campos com coluna local e valor externo presente), `extras` (campos sem coluna local), `missing` (não encontrados).

## Passo 4 — Aplicação Parcial (Write local)
- Endpoint `POST /api/v1/oamd/implantacoes/<impl_id>/apply` que preenche **somente** os campos locais vazios com valores externos do preview.
- Registra timeline e limpa cache.

## Passo 5 — UI de Consulta
- O botão “Consultar” no modal chama `preview_full` e exibe tudo: aplicáveis/extras/ausentes.
- “Aplicar” preenche apenas os aplicáveis.

## Observabilidade
- Logs do inventário (tabelas/colunas encontradas), mapeamento e operações de preview/apply.

## Segurança
- Consultas ao OAMD sempre read-only; rate-limit; owner/gestão.

## Esforço
- Inventário + mapeamento + preview: 0.5–1 dia.
- Apply + UI: 0.5 dia.

## Entrega Inicial
- Rodar Passo 1–3 para lhe apresentar um relatório de todas as tabelas e colunas acessíveis, com os campos do print que conseguimos obter. Em seguida, avançamos para o apply e UI.