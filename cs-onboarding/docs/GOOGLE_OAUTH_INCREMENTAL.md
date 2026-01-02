# Autorização Incremental do Google OAuth 2.0

## 📋 Visão Geral

Este documento descreve a implementação da **Autorização Incremental** do Google OAuth 2.0 no projeto CS Onboarding.

## 🎯 O que é Autorização Incremental?

A autorização incremental permite que você solicite permissões (escopos) do Google apenas quando realmente precisar delas, melhorando a experiência do usuário.

### Benefícios:
- ✅ **Melhor UX**: Usuários não são bombardeados com solicitações de permissão no login
- ✅ **Maior taxa de conversão**: Menos permissões = menos resistência
- ✅ **Segurança**: Princípio do menor privilégio
- ✅ **Flexibilidade**: Adicione novos recursos sem re-autenticar todos os usuários

## 🏗️ Arquitetura

### Fluxo de Autorização

```
1. LOGIN INICIAL
   └─> Solicita apenas: openid, email, profile
   └─> Usuário faz login e acessa o sistema

2. ACESSO À AGENDA (quando necessário)
   └─> Verifica se usuário já tem escopo de calendar
   └─> Se não tiver, solicita incrementalmente
   └─> Google combina escopos antigos + novos
   └─> Token resultante tem TODOS os escopos
```

### Componentes Implementados

#### 1. **Serviço de OAuth** (`backend/project/domain/google_oauth_service.py`)
- Gerenciamento de tokens
- Refresh automático
- Armazenamento persistente
- Verificação de escopos

#### 2. **Tabela de Tokens** (`google_tokens`)
```sql
CREATE TABLE google_tokens (
    id INTEGER PRIMARY KEY,
    usuario TEXT UNIQUE,
    access_token TEXT,
    refresh_token TEXT,
    token_type TEXT,
    expires_at TIMESTAMP,
    scopes TEXT,  -- Escopos concedidos
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### 3. **Configuração** (`config.py`)
```python
# Escopos básicos (login)
GOOGLE_OAUTH_SCOPES_BASIC = 'openid email profile'

# Escopos adicionais (incrementais)
GOOGLE_OAUTH_SCOPES_CALENDAR = 'https://www.googleapis.com/auth/calendar'
GOOGLE_OAUTH_SCOPES_DRIVE_FILE = 'https://www.googleapis.com/auth/drive.file'
```

## 🚀 Como Usar

### Login Inicial (Escopos Básicos)

O login com Google solicita apenas escopos básicos:

```python
# Em __init__.py
oauth.register(
    name='google',
    client_kwargs={
        'scope': 'openid email profile',  # Apenas básicos
        'include_granted_scopes': 'true',  # Habilita incremental
        'access_type': 'offline',  # Para refresh_token
    }
)
```

### Solicitar Escopo Adicional (Ex: Calendar)

Quando o usuário tenta acessar a agenda:

```python
# Em agenda.py
@agenda_bp.route('/agenda/connect')
def agenda_connect():
    # Verifica se já tem o escopo
    if user_has_scope(g.user_email, SCOPE_CALENDAR):
        flash('Você já está conectado!')
        return redirect(url_for('agenda.agenda_home'))
    
    # Solicita incrementalmente
    return oauth.google.authorize_redirect(
        redirect_uri,
        scope=SCOPE_CALENDAR,  # Apenas calendar
        include_granted_scopes='true'  # INCREMENTAL
    )
```

### Usar Token com Refresh Automático

```python
# Em qualquer lugar que precise do token
from backend.project.domain.google_oauth_service import get_valid_token

token = get_valid_token(user_email)
# Token é automaticamente renovado se expirado
```

## 📊 Funções Principais

### `get_valid_token(user_email)`
Obtém um token válido, renovando automaticamente se expirado.

### `user_has_scope(user_email, scope)`
Verifica se o usuário já concedeu um escopo específico.

### `save_user_google_token(user_email, token)`
Salva ou atualiza o token no banco de dados.

### `refresh_google_token(user_email, refresh_token)`
Renova um token expirado usando o refresh_token.

### `revoke_google_token(user_email)`
Revoga todos os escopos concedidos pelo usuário.

## 🔧 Configuração

### Variáveis de Ambiente (.env)

```bash
# Google OAuth
GOOGLE_CLIENT_ID=seu-client-id
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Escopos (opcional - padrão é apenas básicos)
GOOGLE_OAUTH_SCOPES=openid email profile
```

### Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Vá em **APIs & Services** > **Credentials**
3. Configure **OAuth 2.0 Client ID**
4. Adicione URIs de redirecionamento:
   - `http://localhost:5000/auth/google/callback` (dev)
   - `http://localhost:5000/agenda/callback` (dev)
   - `https://seu-dominio.com/auth/google/callback` (prod)
   - `https://seu-dominio.com/agenda/callback` (prod)

## 📝 Migração do Banco de Dados

Execute o script de migração:

```bash
python apply_google_tokens_migration.py
```

Ou manualmente:

```bash
sqlite3 instance/csapp.db < migrations/create_google_tokens_table.sql
```

## 🔍 Exemplo de Fluxo Completo

### 1. Usuário faz login
```
GET /login/google
  ↓
Google solicita: openid, email, profile
  ↓
Usuário autoriza
  ↓
Callback: /auth/google/callback
  ↓
Token salvo no banco com escopos básicos
  ↓
Usuário logado no sistema
```

### 2. Usuário acessa Agenda
```
GET /agenda
  ↓
Sistema verifica: user_has_scope(email, 'calendar')
  ↓
Não tem → Mostra botão "Conectar Google Calendar"
```

### 3. Usuário conecta Calendar
```
GET /agenda/connect
  ↓
Google solicita: calendar (incremental)
  ↓
Google mostra: "Permitir acesso ao Calendar?"
  ↓
Usuário autoriza
  ↓
Callback: /agenda/callback
  ↓
Token atualizado no banco com escopos combinados:
  - openid
  - email
  - profile
  - https://www.googleapis.com/auth/calendar
  ↓
Agenda funciona!
```

## 🎨 Adicionando Novos Escopos

Para adicionar suporte a Google Drive, por exemplo:

### 1. Adicionar constante em `config.py`
```python
GOOGLE_OAUTH_SCOPES_DRIVE = 'https://www.googleapis.com/auth/drive.file'
```

### 2. Criar rota de conexão
```python
@drive_bp.route('/drive/connect')
@login_required
def drive_connect():
    from ..domain.google_oauth_service import user_has_scope, SCOPE_DRIVE_FILE
    
    if user_has_scope(g.user_email, SCOPE_DRIVE_FILE):
        flash('Já conectado ao Drive!')
        return redirect(url_for('drive.home'))
    
    return oauth.google.authorize_redirect(
        url_for('drive.callback', _external=True),
        scope=SCOPE_DRIVE_FILE,
        include_granted_scopes='true'
    )
```

### 3. Criar callback
```python
@drive_bp.route('/drive/callback')
def drive_callback():
    token = oauth.google.authorize_access_token()
    save_user_google_token(g.user_email, token)
    flash('Drive conectado!')
    return redirect(url_for('drive.home'))
```

## ⚠️ Notas Importantes

### Refresh Tokens
- O Google só envia `refresh_token` na primeira autorização
- Use `access_type='offline'` para garantir refresh_token
- Use `prompt='consent'` para forçar nova tela de consentimento

### Revogação
- Revogar um token revoga **TODOS** os escopos
- Usuário precisará re-autorizar tudo

### Expiração
- Access tokens expiram em ~1 hora
- O sistema renova automaticamente usando refresh_token
- Tokens são considerados expirados 5 minutos antes para segurança

## 🐛 Troubleshooting

### "Token expirado"
- Verifique se o refresh_token está sendo salvo
- Confirme que `access_type='offline'` está configurado

### "Escopo não encontrado"
- Verifique se `include_granted_scopes='true'` está configurado
- Confirme que o token foi salvo corretamente no banco

### "Redirect URI mismatch"
- Verifique se a URI está cadastrada no Google Cloud Console
- Em produção, use HTTPS
- A URI deve ser EXATAMENTE igual (incluindo trailing slash)

## 📚 Referências

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Incremental Authorization](https://developers.google.com/identity/protocols/oauth2/web-server#incrementalAuth)
- [OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)

## ✅ Checklist de Implementação

- [x] Criar serviço de OAuth (`google_oauth_service.py`)
- [x] Criar tabela `google_tokens`
- [x] Atualizar configuração para escopos separados
- [x] Modificar login para usar apenas escopos básicos
- [x] Implementar autorização incremental na agenda
- [x] Adicionar refresh automático de tokens
- [x] Criar script de migração
- [x] Documentar implementação

## 🎉 Conclusão

A autorização incremental está implementada e pronta para uso! Os usuários agora terão uma experiência mais suave, com solicitações de permissão apenas quando necessário.
