# Frontend

Este diretório concentra toda a camada de UI do projeto.

## Estrutura

- `templates/`: Templates Jinja2 usados pelo Flask.
- `static/`: Arquivos estáticos (CSS, JS, imagens, fontes).

## Convenções de Templates

- Use `base.html` como layout principal e estenda via `{% extends 'base.html' %}`.
- Componentize blocos comuns em `templates/partials/` e `templates/modals/`.
- Evite lógica complexa em templates; mantenha validações e sanitizações no backend.

## Convenções de Assets

- CSS próprio em `static/css/` e JS próprio em `static/js/`.
- Prefira CDNs aprovados na CSP (jsDelivr, unpkg, Google Fonts).
- Imagens em `static/imagens/`.

## Integração com Flask

O Flask foi configurado para buscar templates e estáticos em:

- `template_folder='../frontend/templates'`
- `static_folder='../frontend/static'`

Links nos templates devem usar `{{ url_for('static', filename='css/arquivo.css') }}`.

## Futuro: Bundler (Vite/Webpack)

- Podemos adicionar um bundler para empacotar JS/CSS modernos.
- A saída seria configurada para `static/` para não impactar o Flask.
- Sugestão de estrutura:
  - `frontend/src/` (código fonte)
  - `frontend/static/` (build/saída)