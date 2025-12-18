# 🔍 Guia de Diagnóstico OAMD

## 📋 Scripts Criados

Criei 2 scripts para diagnosticar problemas com as datas do OAMD:

### 1. `diagnostico_oamd.py` (Interativo)
```bash
python diagnostico_oamd.py
# Vai pedir o ID Favorecido
```

### 2. `diagnostico_oamd_auto.py` (Automático)
```bash
python diagnostico_oamd_auto.py 11350
# Passa o ID direto
```

## ⚠️ Requisitos

**IMPORTANTE:** Estes scripts precisam de:
- ✅ Conexão com o banco externo OAMD
- ✅ VPN conectada (se necessário)
- ✅ Variáveis de ambiente configuradas (`EXTERNAL_DB_URL`)

## 🚀 Como Usar

### Opção A: Em Produção (Recomendado)
1. Fazer SSH no servidor de produção
2. Navegar até o diretório do projeto
3. Executar: `python diagnostico_oamd_auto.py 11350`

### Opção B: Local com VPN
1. Conectar à VPN
2. Configurar `EXTERNAL_DB_URL` no `.env`
3. Executar: `python diagnostico_oamd_auto.py 11350`

### Opção C: Via Interface Web
1. Abrir o site em produção
2. Criar/abrir uma implantação com ID Favorecido 11350
3. Abrir "Detalhes da Empresa"
4. Clicar em "Consultar"
5. Abrir DevTools (F12) → Network → Ver requisição `/api/v1/oamd/implantacoes/.../consulta`
6. Ver a resposta JSON

## 📊 O que o Script Mostra

O script vai mostrar:

### 1. Dados Brutos do Banco Externo
```
📅 inicioimplantacao        = 2025-12-03
📅 inicioproducao          = 2025-12-01
📅 finalimplantacao        = (vazio)
📅 datacadastro            = 2024-11-15
```

### 2. Dados Mapeados
```
✅ Início da Implantação    = 2025-12-03
✅ Início em Produção       = 2025-12-01
❌ Fim da Implantação       = NÃO MAPEADO
✅ Data de Cadastro         = 2024-11-15
```

### 3. Problemas Encontrados
```
🚨 PROBLEMAS:
   ⚠️  Data de Início da Implantação não mapeada
   
💡 CAMPOS DE DATA DISPONÍVEIS:
   - inicioimplantacao
   - inicioproducao
   - datacadastro
```

### 4. Arquivo JSON
Salva um arquivo `diagnostico_oamd_11350.json` com todos os dados para análise.

## 🔧 Próximos Passos

Após executar o script:

1. **Verificar quais campos de data existem** no banco externo
2. **Comparar com o mapeamento** em `external_service.py` (linhas 137-139)
3. **Adicionar campos faltantes** se necessário
4. **Corrigir o mapeamento** para usar os nomes corretos

## 📝 Exemplo de Correção

Se o script mostrar que o campo é `inicioimplantacao` mas não está sendo mapeado:

**Antes** (`external_service.py` linha 138):
```python
mapped['data_inicio_efetivo'] = find_value(['iniciodeproducao', 'inicio_implantacao'])
```

**Depois**:
```python
mapped['data_inicio_efetivo'] = find_value(['inicioimplantacao', 'inicio_implantacao', 'iniciodeproducao'])
```

## 🎯 Objetivo

O objetivo é garantir que:
- ✅ Todas as datas do OAMD sejam encontradas
- ✅ Sejam mapeadas corretamente
- ✅ Sejam exibidas no modal
- ✅ Sejam salvas no banco ao aplicar
- ✅ Cálculo de "Dias" use a data correta

## 💡 Dica

Se não conseguir executar o script, você pode:
1. Abrir o site em produção
2. Abrir DevTools (F12)
3. Ir para Console
4. Executar:
```javascript
fetch('/api/v1/oamd/implantacoes/0/consulta?id_favorecido=11350')
  .then(r => r.json())
  .then(data => console.log(JSON.stringify(data, null, 2)));
```

Isso vai mostrar os mesmos dados que o script Python.
