# 🎯 GUIA COMPLETO: Importação Proposta Suite → Redmine

## 📋 Resumo

Este guia mostra como:

1. ✅ Gerar chave API do Redmine
2. ✅ Criar projeto "Proposta Suite" via Python
3. ✅ Importar 40 tarefas do CSV para o Redmine

---

## 🔑 PASSO 1: Gerar Chave API do Redmine

### Como gerar a chave:

1. **Acesse o Redmine:**

   ```
   http://localhost:3001
   ```

2. **Faça login:**

   - Usuário: `admin`
   - Senha: `admin`

3. **Acesse sua conta:**

   - Clique em **"My account"** (canto superior direito)

4. **API Access Key:**

   - No menu lateral direito, clique em: **"API access key"**
   - Clique no botão: **"Show"**
   - **Copie a chave** (40 caracteres hexadecimais)

   Exemplo de chave:

   ```
   c3b019acd201f0f16ef9f3aee064979424dda254
   ```

---

## 📝 PASSO 2: Configurar o Script de Importação

1. **Abra o arquivo:**

   ```bash
   code /home/erics/TEMP/CODIGOS/redmine-6.0.5/import_proposta_suite.py
   ```

2. **Na linha 16, substitua:**

   ```python
   API_KEY = 'COLOQUE_SUA_CHAVE_API_AQUI'
   ```

   **Por:**

   ```python
   API_KEY = 'sua_chave_copiada_do_redmine'
   ```

3. **Salve o arquivo** (Ctrl+S)

---

## 🚀 PASSO 3: Executar a Importação

### Ativar ambiente virtual e rodar:

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
source .venv-redmine/bin/activate
python3 import_proposta_suite.py
```

### O que o script faz:

1. ✅ Conecta ao Redmine via API
2. ✅ Cria projeto "Proposta Suite" (identifier: `proposta-suite`)
3. ✅ Lê arquivo CSV: `projeto/proposta_suite_redmine_tasks.csv`
4. ✅ Importa 40 tarefas organizadas por fase:
   - **Discovery:** 10 tarefas
   - **Delivery Backend:** 18 tarefas
   - **Delivery Frontend:** 10 tarefas
   - **Scale:** 6 tarefas

---

## 📊 PASSO 4: Verificar Importação

Após a execução, acesse:

```
http://localhost:3001/projects/proposta-suite
```

Você verá:

- ✅ Projeto "Proposta Suite" criado
- ✅ 40 issues importadas
- ✅ Issues organizadas por tracker (Task/Feature/Bug)
- ✅ Status corretos (New, In Progress, Closed)

---

## 🔧 Estrutura do Script

### Configurações principais:

```python
REDMINE_URL = 'http://localhost:3001'
API_KEY = 'sua_chave_api'

PROJECT_IDENTIFIER = 'proposta-suite'
PROJECT_NAME = 'Proposta Suite'
PROJECT_DESCRIPTION = 'MVP FastAPI + Vue 3 para propostas imobiliárias'

CSV_FILE = 'projeto/proposta_suite_redmine_tasks.csv'
```

### Mapeamentos:

| CSV Status  | Redmine Status ID | Nome         |
| ----------- | ----------------- | ------------ |
| New         | 1                 | Novo         |
| In Progress | 2                 | Em Progresso |
| Closed      | 5                 | Fechado      |

| CSV Tracker | Redmine Tracker ID | Nome           |
| ----------- | ------------------ | -------------- |
| Task        | 2                  | Tarefa         |
| Feature     | 1                  | Funcionalidade |
| Bug         | 3                  | Erro           |

---

## 📦 Bibliotecas Instaladas

```bash
pip install python-redmine pandas
```

### Dependências:

- `python-redmine==2.5.0` - Cliente Python para API REST do Redmine
- `pandas==2.3.3` - Processamento de dados (CSV)
- `requests==2.32.5` - HTTP requests

---

## 🔍 Exemplo de Uso da API Python-Redmine

### Conectar:

```python
from redminelib import Redmine

redmine = Redmine('http://localhost:3001', key='SUA_CHAVE_API')
user = redmine.user.get('current')
print(f"Conectado como: {user.firstname} {user.lastname}")
```

### Criar Projeto:

```python
project = redmine.project.create(
    name='Proposta Suite',
    identifier='proposta-suite',
    description='MVP FastAPI + Vue 3',
    is_public=True
)
```

### Criar Issue:

```python
issue = redmine.issue.create(
    project_id='proposta-suite',
    subject='D-01: Pesquisa de mercado',
    description='Análise de concorrentes',
    tracker_id=2,  # Task
    status_id=5    # Closed
)
```

### Listar Issues:

```python
issues = redmine.issue.filter(project_id='proposta-suite')
for issue in issues:
    print(f"#{issue.id}: {issue.subject}")
```

---

## ⚠️ Troubleshooting

### Erro: "ResourceNotFoundError"

- ✅ Verifique se o servidor Redmine está rodando
- ✅ URL correta: `http://localhost:3001`

### Erro: "Unauthorized"

- ✅ Chave API inválida ou expirada
- ✅ Gere nova chave: My Account > API access key > Reset

### Erro: "FileNotFoundError"

- ✅ Verifique caminho do CSV: `projeto/proposta_suite_redmine_tasks.csv`
- ✅ Execute o script do diretório correto

### Script não encontra módulos:

```bash
# Ative o ambiente virtual primeiro:
source .venv-redmine/bin/activate
python3 import_proposta_suite.py
```

---

## 📖 Documentação Oficial

- **Redmine API:** https://www.redmine.org/projects/redmine/wiki/Rest_api
- **Python-Redmine:** https://python-redmine.com/
- **Endpoints disponíveis:**
  - Projects: `/projects.json`
  - Issues: `/issues.json`
  - Users: `/users/current.json`
  - Trackers: `/trackers.json`
  - Issue Statuses: `/issue_statuses.json`

---

## 🎉 Próximos Passos

Após importar as tarefas:

1. ✅ **Organize o workflow:**

   - Crie versões (milestones)
   - Configure categorias
   - Defina membros do projeto

2. ✅ **Configure integrações:**

   - Webhooks para notificações
   - Git repositories
   - Roadmap e Gantt chart

3. ✅ **Automatize:**
   - Scripts para atualização de status
   - Sincronização com outros sistemas
   - Reports automatizados

---

## 💡 Dicas

- ✅ Use `identifier` único para cada projeto
- ✅ API key é pessoal - cada usuário tem a sua
- ✅ Tracker_id e Status_id podem variar entre instalações
- ✅ Para verificar IDs disponíveis:
  ```python
  trackers = redmine.tracker.all()
  statuses = redmine.issue_status.all()
  ```

---

**Autor:** Script gerado para importação automatizada  
**Data:** 27/11/2025  
**Versão:** 1.0
