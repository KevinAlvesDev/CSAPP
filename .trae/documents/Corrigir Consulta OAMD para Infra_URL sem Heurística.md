## Objetivo
Trazer os valores reais do OAMD (Infra e URL) para cada ID Favorecido sem depender de input manual, usando fontes oficiais do schema e correlação exata.

## Ajustes Propostos
1. Correlação exata
- Executar duas consultas separadas:
  - Query A: `SELECT ... FROM empresafinanceiro WHERE codigo = :id LIMIT 1`
  - Query B (fallback): `SELECT ... FROM empresafinanceiro WHERE codigofinanceiro = :id LIMIT 1`
- Usar o primeiro resultado disponível; sem `ORDER BY` heurístico.

2. Fontes oficiais
- Infra:
  - Prioridade 0: `url_integracao` (se existir no OAMD – usaremos exatamente o campo oficial para URL)
  - Prioridade 1: `nomeempresazw` (regex estrita `ZW_###`)
  - Prioridade 2: `empresazw` (numérico → `ZW_<num>`)
- URL:
  - Prioridade 0: `url_integracao` (se existir)
  - Prioridade 1: composta de `ZW_###` → `http://zw<###>.pactosolucoes.com.br/app`

3. Sem heurística ampla
- Remover varredura de “todos os campos”. Apenas os campos oficiais serão considerados para evitar valores falsos.

4. Observabilidade
- Logar para cada consulta: ID Favorecido, critério usado (codigo/codigofinanceiro), valores crus (`nomeempresazw`, `empresazw`, `url_integracao`) e a decisão final.

5. Persistência automática
- Após “Consultar”, persistir `informacao_infra` e `tela_apoio_link` no registro da implantação.

## Validação
- Testar com 11287 e 11350, confirmando que os valores retornados batem com os dados do OAMD.
- Adicionar teste automatizado que chama a query A/B e compara com os campos oficiais.

## Benefício
- A consulta deixa de “tentar adivinhar”; usa somente as colunas oficiais. Cada ID Favorecido retorna seus valores reais sem qualquer intervenção manual.

## Aprovação
- Ao aprovar, implemento as queries separadas, extração estrita, logs e testes; depois aciono a persistência com o botão “Consultar” já existente.