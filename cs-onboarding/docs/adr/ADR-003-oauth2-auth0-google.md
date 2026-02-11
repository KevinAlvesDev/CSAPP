# ADR-003: OAuth2 com Auth0 + Google

**Status:** Aceita  
**Data:** 2025-01-01  
**Decisores:** Time de Desenvolvimento

## Contexto

O sistema precisa de autenticação segura com suporte a:

1. Autenticação corporativa (domínio da empresa)
2. Integração com Google Calendar (para agenda de implantações)
3. Desenvolvimento local sem dependência de serviços externos
4. Gerenciamento de perfis e permissões (RBAC)

## Decisão

Implementamos um sistema de autenticação híbrido:

1. **Auth0** — Autenticação principal em produção (SSO corporativo)
2. **Google OAuth 2.0** — Login alternativo + integração com Google Calendar
3. **Login local** — Modo desenvolvimento (bypass de auth)

## Justificativa

### Auth0
- **SSO corporativo**: Permite integrar com Active Directory / G Suite
- **Gerenciamento de usuários**: Dashboard admin sem código
- **MFA**: Multi-factor authentication out-of-the-box
- **Compliance**: Certificações SOC 2, HIPAA, etc.
- **Custo**: Free tier suficiente para o volume atual

### Google OAuth (complementar)
- **Google Calendar**: Necessário para a feature de agenda de implantações
- **Autorização incremental**: Solicita permissões conforme necessário
  - Login: `openid email profile` (básico)
  - Agenda: `calendar` (solicitado ao acessar módulo de agenda)
  - Drive: `drive.file` (solicitado para uploads/exports)
- **Familiar**: Usuários já possuem conta Google corporativa

### Login Local (Desenvolvimento)
- Auth0 é **automaticamente desabilitado** quando `USE_SQLITE_LOCALLY=True`
- Usuário admin criado automaticamente no startup
- Zero configuração para começar a desenvolver

## Implementação

### Fluxo de Autenticação

```
┌──────┐     ┌──────────┐     ┌────────┐
│ User │────▶│ /login   │────▶│ Auth0  │
│      │     │          │     │ ou     │
│      │     │          │────▶│ Google │
└──────┘     └──────────┘     └────┬───┘
                                   │
                              callback
                                   │
                              ┌────▼───┐
                              │/callback│
                              │ _sync_  │
                              │_profile │
                              └────┬───┘
                                   │
                              ┌────▼───────┐
                              │ session +  │
                              │ perfil_    │
                              │ usuario    │
                              └────────────┘
```

### RBAC (Role-Based Access Control)

Os perfis de acesso são gerenciados na tabela `perfil_usuario`:

| Perfil | Permissões |
|--------|------------|
| Administrador | Acesso total, gerenciamento de usuários |
| Gerente | Visão de todas as implantações, analytics |
| Coordenador | Visão por equipe |
| Implantador | Apenas implantações atribuídas |

### Decisões de Segurança

1. **Session-based**: Usamos sessions do Flask (server-side) ao invés de JWT stateless
   - Motivo: SSR com Jinja2 funciona melhor com sessions
   - Cookie: `HttpOnly`, `Secure` (produção), `SameSite=Lax`

2. **CSRF Protection**: Flask-WTF CSRFProtect em todos os formulários
   - APIs REST isentas (`api_v1_bp`, `health_bp`)
   - APIs não isentas de CSRF deliberadamente (`checklist_bp`) para proteger mutações

3. **Master Admin**: Email específico (`MASTER_ADMIN_EMAIL`) sempre recebe perfil Admin
   - Prevenção contra lock-out acidental
   - Verificação em `before_request`

## Consequências

### Positivas
- Autenticação robusta sem gerenciar senhas diretamente
- SSO corporativo simplifica onboarding de usuários
- Google Calendar integrado nativamente
- Desenvolvimento local sem obstáculos de auth

### Negativas
- Dependência de serviço externo (Auth0) em produção
- Duas integrações OAuth para manter (Auth0 + Google)
- Complexidade no fluxo de autorização incremental
- Session server-side requer storage (mas Redis resolve para scale)

### Riscos
- Auth0 free tier tem limite de usuários (7.000 MAU)
- Google pode mudar APIs de OAuth (historicamente estável)
- **Mitigação**: Abstração via Authlib permite trocar provider com mínimo impacto

## Alternativas Rejeitadas

1. **Apenas Google OAuth**: Não oferece SSO corporativo nem dashboard admin
2. **Firebase Auth**: Acoplaria ao ecossistema Google/Firebase inteiro
3. **Auth própria (email+senha)**: Risco de segurança, mais código para manter
4. **Keycloak (self-hosted)**: Complexidade operacional de manter infraestrutura auth
