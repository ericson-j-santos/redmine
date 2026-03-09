# 📊 GUIA COMPLETO DE ANÁLISE E USO DO REDMINE - PROPOSTA SUITE

## 🎯 O QUE JÁ TEMOS

### ✅ Projeto Configurado

- **44 tarefas importadas** organizadas por fase
- **Status atualizados** conforme CSV original
- **API REST habilitada** para integrações
- **E-mail SMTP configurado** (Gmail)

---

## 📈 ANÁLISES DISPONÍVEIS

### 1. **Análise Completa Automatizada**

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
source .venv-redmine/bin/activate
python3 analise_proposta_suite.py
```

**Fornece:**

- 📊 Estatísticas gerais (total, concluídas, pendentes)
- 📈 Distribuição por status (Nova, Em andamento, Fechada)
- 🔹 Análise por fase (Discovery, Backend, Frontend, Scale)
- 🏷️ Distribuição por tipo (Tracker)
- ⏰ Timeline de criação e atualizações
- ⚠️ Lista de tarefas pendentes
- 📄 **Exportação para CSV** (para apresentações/relatórios)

**Por que usar:**

- Visão macro do projeto em segundos
- Métricas para reuniões de status
- Identificação rápida de gargalos
- Dados prontos para dashboards

---

### 2. **Análise na Interface Web**

#### **Visão Geral do Projeto**

🌐 http://localhost:3001/projects/proposta-suite

**Oferece:**

- Resumo visual do projeto
- Activity feed (atividades recentes)
- Wiki do projeto (documentação)
- Roadmap e milestones

#### **Lista de Issues**

🌐 http://localhost:3001/projects/proposta-suite/issues

**Recursos:**

- **Filtros avançados**: Status, Tracker, Autor, Data
- **Agrupamento**: Por fase, status, tracker, prioridade
- **Ordenação**: Por ID, data, prioridade, atribuído
- **Visualizações personalizadas**: Salvar filtros favoritos

**Como filtrar:**

```
- Apenas tarefas abertas: Status != Fechada
- Por fase: Adicionar campo customizado "Fase"
- Tarefas críticas: Prioridade = Alta
- Minhas tarefas: Atribuído a = Meu usuário
```

#### **Gantt Chart**

🌐 http://localhost:3001/projects/proposta-suite/issues/gantt

**Mostra:**

- Timeline visual das tarefas
- Dependências entre tarefas
- Duração e datas de entrega
- Progresso geral do projeto

**Por que usar:**

- Planejamento visual
- Identificar overlaps
- Comunicação com stakeholders

#### **Calendário**

🌐 http://localhost:3001/projects/proposta-suite/issues/calendar

**Mostra:**

- Tarefas agrupadas por data
- Deadlines próximos
- Carga de trabalho por período

---

### 3. **Relatórios Customizados**

#### **Via Interface (Admin > Reports)**

- 📊 Tempo gasto por tarefa
- 📈 Issues criadas vs resolvidas
- 👥 Produtividade por membro
- 📅 Burndown chart (se configurar sprints)

#### **Via API/Python**

Criar scripts personalizados:

```python
# Exemplo: Tarefas por prioridade
from redminelib import Redmine

redmine = Redmine('http://localhost:3001', key='SUA_API_KEY')
issues = redmine.project.get('proposta-suite').issues

for priority in ['Baixa', 'Normal', 'Alta', 'Urgente']:
    count = sum(1 for i in issues if i.priority.name == priority)
    print(f"{priority}: {count} tarefas")
```

---

## 🔍 MÉTRICAS IMPORTANTES

### **1. Taxa de Conclusão**

```
(Tarefas Fechadas / Total de Tarefas) × 100
```

**Indica:** Progresso geral do projeto

### **2. Velocidade de Entrega**

```
Tarefas Fechadas / Dias de Projeto
```

**Indica:** Ritmo da equipe, base para estimativas

### **3. Tempo Médio de Resolução**

```
Soma(Data Fechamento - Data Criação) / Tarefas Fechadas
```

**Indica:** Eficiência, complexidade média

### **4. Taxa de Reabertura**

```
(Tarefas Reabertas / Tarefas Fechadas) × 100
```

**Indica:** Qualidade das entregas

### **5. Distribuição por Fase**

```
Tarefas por Fase / Total de Tarefas
```

**Indica:** Onde está o esforço, identificar desequilíbrios

---

## 📧 NOTIFICAÇÕES POR E-MAIL

### **Por que não estou recebendo?**

1. **Configuração da Conta**

   - http://localhost:3001/my/account
   - Verificar: Email preenchido
   - Ir para aba "Email notifications"
   - Marcar: "Para todos os eventos em todos os meus projetos"

2. **Configuração Global (Admin)**

   - http://localhost:3001/settings?tab=notifications
   - Marcar: "Emission of email notifications"
   - Configurar eventos que geram notificação

3. **Problema: Próprias Ações**
   - Redmine NÃO envia emails para ações próprias
   - Se você criou/atualizou, não receberá notificação
   - **Solução**: Pedir outro usuário para comentar/atualizar

### **Testar Notificações**

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
source .venv-redmine/bin/activate
python3 testar_email.py
```

### **Criar Outro Usuário para Teste**

```bash
bundle exec rails runner "
User.create!(
  login: 'teste',
  firstname: 'Usuario',
  lastname: 'Teste',
  mail: 'teste@example.com',
  password: 'senha123',
  password_confirmation: 'senha123',
  admin: false
)
puts 'Usuário teste criado!'
"
```

Depois:

1. Login como `teste` / `senha123`
2. Comentar em uma issue
3. Verificar se admin recebe e-mail

---

## 🚀 PRÓXIMOS PASSOS RECOMENDADOS

### **1. Organização Avançada**

#### **Criar Versões/Milestones**

```python
from redminelib import Redmine

redmine = Redmine('http://localhost:3001', key='SUA_API_KEY')
project = redmine.project.get('proposta-suite')

# Criar milestone
version = redmine.version.create(
    project_id=project.id,
    name='MVP v1.0',
    status='open',
    due_date='2025-12-31',
    description='Entrega do MVP completo'
)

# Associar issues ao milestone
for issue in [1, 2, 3]:  # IDs das issues
    redmine.issue.update(issue, fixed_version_id=version.id)
```

#### **Adicionar Campos Customizados**

- Admin > Custom fields > New custom field
- Exemplo: "Fase" (Discovery, Backend, Frontend, Scale)
- Exemplo: "Complexidade" (Baixa, Média, Alta)
- Exemplo: "Estimativa (horas)"

### **2. Integração com Git**

#### **Fechar Issues via Commit**

```bash
git commit -m "Implementa feature X (fixes #10)"
# Fecha automaticamente issue #10
```

#### **Referenciabr Issues**

```bash
git commit -m "Corrige bug em validação (refs #15)"
# Adiciona referência sem fechar
```

### **3. Automação com Webhooks**

Configurar em **Admin > Settings > Webhooks**:

- Notificar Slack quando issue é fechada
- Disparar CI/CD quando issue de deploy é criada
- Atualizar dashboard externo

### **4. Dashboard Executivo**

Criar script Python que gera relatório HTML:

```python
import matplotlib.pyplot as plt
from jinja2 import Template

# Gerar gráficos com matplotlib
# Gerar HTML com Jinja2
# Enviar por e-mail ou publicar em servidor
```

### **5. Sincronização Bidirecional**

Script para manter CSV e Redmine sincronizados:

- Exportar Redmine → CSV (atualizar planilhas)
- Importar CSV → Redmine (bulk updates)

---

## 📚 SCRIPTS DISPONÍVEIS

| Script                      | Função                        | Comando                             |
| --------------------------- | ----------------------------- | ----------------------------------- |
| `import_proposta_suite.py`  | Importar tarefas do CSV       | `python3 import_proposta_suite.py`  |
| `atualizar_status.py`       | Sincronizar status com CSV    | `python3 atualizar_status.py`       |
| `analise_proposta_suite.py` | Análise completa + CSV export | `python3 analise_proposta_suite.py` |
| `testar_email.py`           | Testar notificações de email  | `python3 testar_email.py`           |

---

## 🔗 INTEGRAÇÃO COM OUTRAS FERRAMENTAS

### **Power BI / Tableau**

- Exportar dados via API
- Criar dashboards interativos
- Análise de tendências

### **Jira (Migração)**

- Exportar issues para formato Jira
- Manter histórico e comentários

### **Trello/Notion**

- Sincronização via API
- Duas views do mesmo projeto

### **CI/CD (GitHub Actions, GitLab CI)**

- Atualizar status automaticamente
- Criar issues de bugs automaticamente

---

## 💡 CASOS DE USO PRÁTICOS

### **Reunião de Sprint**

1. Rodar `analise_proposta_suite.py`
2. Revisar relatório CSV exportado
3. Identificar tarefas "Em andamento" travadas
4. Replanejar próximas tarefas

### **Apresentação para Cliente**

1. Abrir Gantt Chart
2. Mostrar progresso visual
3. Exportar PDF do Gantt
4. Compartilhar relatório CSV

### **Planejamento de Recursos**

1. Filtrar tarefas "Nova"
2. Estimar complexidade
3. Distribuir para equipe
4. Definir milestones

### **Auditoria de Qualidade**

1. Filtrar tarefas "Fechada"
2. Verificar comentários de resolução
3. Identificar padrões de bugs
4. Criar tarefas de melhoria

---

## 🎓 BOAS PRÁTICAS

### **Nomenclatura**

- ✅ **Bom**: `B-01 - Estrutura base backend`
- ❌ **Ruim**: `fazer backend`

### **Descrições**

- Incluir contexto e requisitos
- Adicionar critérios de aceitação
- Linkar documentação relevante

### **Status**

- Atualizar regularmente
- Adicionar comentários explicativos
- Fechar quando realmente concluído

### **Atribuição**

- Sempre atribuir responsável
- Não deixar tarefas "órfãs"
- Revisar atribuições em reuniões

### **Priorização**

- Usar prioridades consistentemente
- Revisar semanalmente
- Justificar mudanças de prioridade

---

## 📞 TROUBLESHOOTING

### **E-mails não chegam**

1. Verificar log: `tail -f log/development.log | grep -i mail`
2. Testar SMTP: `bundle exec rails runner "ActionMailer::Base.deliver_now"`
3. Verificar firewall/antivírus
4. Testar com outro provedor de email

### **API não funciona**

1. Verificar API habilitada: Admin > Settings > Authentication
2. Regenerar API key: My Account > API access key > Reset
3. Testar com curl: `curl -H "X-Redmine-API-Key: SUA_KEY" http://localhost:3001/issues.json`

### **Performance lenta**

1. Limpar cache: `bundle exec rake tmp:cache:clear`
2. Reindexar banco: `bundle exec rake db:migrate`
3. Otimizar queries: Adicionar índices

---

## 🌟 CONCLUSÃO

Com Redmine + Python você tem:

1. ✅ **Rastreabilidade completa** de todas as tarefas
2. 📊 **Métricas automáticas** para decisões baseadas em dados
3. 🔗 **Integração** com ferramentas existentes
4. 📧 **Notificações** automáticas de mudanças
5. 📈 **Visualizações** para diferentes stakeholders
6. 🤖 **Automação** de tarefas repetitivas

**Próximo nível:**

- Integrar com repositório Git
- Criar dashboard em tempo real
- Automatizar relatórios semanais
- Configurar alertas de prazo
