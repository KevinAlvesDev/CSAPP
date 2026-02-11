# ADR-001: Flask como Framework Web

**Status:** Aceita  
**Data:** 2025-01-01  
**Decisores:** Time de Desenvolvimento

## Contexto

Precisávamos escolher um framework web Python para o sistema de onboarding. Os principais candidatos eram:

1. **Flask** — Microframework leve e flexível
2. **FastAPI** — Framework moderno com async/await nativo e OpenAPI
3. **Django** — Framework full-stack com ORM e admin

## Decisão

Escolhemos **Flask** como framework web principal.

## Justificativa

### Por que Flask e não FastAPI?

1. **Server-Side Rendering (SSR)**: O sistema usa templates Jinja2 (SSR) extensivamente. Flask/Jinja2 é a combinação mais madura e documentada para esse padrão.

2. **Curva de Aprendizado**: O time já tinha experiência com Flask. FastAPI exigiria aprendizado de async/await, Pydantic models e conceitos de concorrência.

3. **Ecossistema de Extensões**: Flask tem extensões maduras que usamos (Flask-WTF, Flask-Limiter, Flask-Caching, Flask-Compress, Flask-Talisman).

4. **Padrão Síncrono**: O sistema é predominantemente I/O-bound com PostgreSQL, mas o padrão síncrono é suficiente para a escala atual.

5. **Simplicidade**: Para um sistema interno com ~50 usuários simultâneos, a performance de async não justifica a complexidade adicional.

### Por que não Django?

1. **ORM não necessário**: Usamos SQL direto (queries customizadas) ao invés de ORM, que é o ponto forte do Django.
2. **Overhead**: Django inclui muitos componentes que não usaríamos (admin, forms, etc.).
3. **Flexibilidade**: Flask permite estruturar o projeto como preferirmos (domain-driven design com services).

## Consequências

### Positivas
- Flexibilidade total na arquitetura
- Baixo overhead no framework
- Fácil integração com Auth0, Google OAuth, R2
- Templates Jinja2 maduros e bem documentados

### Negativas
- Sem validação automática de request/response (precisa ser manual)
- Sem documentação OpenAPI automática (criada manualmente via api_docs)
- Async não disponível nativamente (mas não é necessário atualmente)
- Mais boilerplate para funcionalidades que Django/FastAPI oferecem out-of-the-box

### Riscos
- Se a escala crescer significativamente (>500 usuários simultâneos), pode ser necessário reavaliar para FastAPI ou adicionar async workers.

## Alternativas Consideradas

| Critério | Flask | FastAPI | Django |
|----------|-------|---------|--------|
| SSR com Jinja2 | ✅ Nativo | ⚠️ Possível | ✅ Nativo |
| API REST | ⚠️ Manual | ✅ Automático | ⚠️ DRF |
| Async | ❌ | ✅ Nativo | ⚠️ Parcial |
| Extensões | ✅ Maduro | ⚠️ Crescendo | ✅ Maduro |
| Curva de Aprendizado | ✅ Baixa | ⚠️ Média | ⚠️ Média |
| Performance | ⚠️ OK | ✅ Alta | ⚠️ OK |
