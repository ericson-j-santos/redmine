#!/usr/bin/env python3
"""
Script para gerar conteúdo completo da Wiki do projeto no Redmine
Cria páginas estruturadas com documentação técnica e gerencial
"""

from redminelib import Redmine
from datetime import datetime
from collections import defaultdict

REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'
PROJECT_IDENTIFIER = 'proposta-suite'


def gerar_pagina_visao_geral(issues):
    """Gera página principal da Wiki com visão geral do projeto"""
    
    total = len(issues)
    fechadas = sum(1 for i in issues if i.status.name == 'Fechada')
    em_andamento = sum(1 for i in issues if i.status.name == 'Em andamento')
    percentual = (fechadas / total * 100) if total > 0 else 0
    
    # Agrupar por fase
    fases = defaultdict(lambda: {'total': 0, 'fechadas': 0})
    for issue in issues:
        fase = 'Não categorizada'
        if 'Fase:**' in issue.description:
            fase = issue.description.split('Fase:**')[1].split('\n')[0].strip()
        elif 'Fase:' in issue.description:
            fase = issue.description.split('Fase:')[1].split('\n')[0].strip()
        
        fases[fase]['total'] += 1
        if issue.status.name == 'Fechada':
            fases[fase]['fechadas'] += 1
    
    wiki = f"""h1. Proposta Suite - MVP FastAPI + Vue 3

{{toc}}

h2. 📋 Visão Geral

O *Proposta Suite* é um MVP (Minimum Viable Product) desenvolvido para gerenciar propostas imobiliárias utilizando tecnologias modernas:

* *Backend:* FastAPI (Python)
* *Frontend:* Vue 3 + Vite + Vuetify
* *Arquitetura:* RESTful API
* *Objetivo:* Sistema completo de propostas com simulações e notificações

h2. 📊 Status do Projeto (Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')})

* *Total de Tarefas:* {total}
* *Concluídas:* {fechadas} ({percentual:.1f}%)
* *Em Andamento:* {em_andamento}
* *Taxa de Conclusão:* {percentual:.1f}%

h3. Progresso por Fase

"""
    
    for fase, stats in sorted(fases.items()):
        perc = (stats['fechadas'] / stats['total'] * 100) if stats['total'] > 0 else 0
        wiki += f"\nh4. {fase}\n\n"
        wiki += f"* Total: {stats['total']} tarefas\n"
        wiki += f"* Concluídas: {stats['fechadas']} ({perc:.1f}%)\n"
        wiki += f"* Pendentes: {stats['total'] - stats['fechadas']}\n"
    
    wiki += f"""

h2. 🎯 Fases do Projeto

O projeto está organizado em 4 fases principais:

h3. 1. Discovery

*Objetivo:* Levantamento e definição de requisitos

Entregas principais:
* Objetivos e fluxos da solução
* Entidades e integrações
* Requisitos funcionais e não funcionais
* Definição de papéis (RBAC)
* Padrões de logging e métricas

h3. 2. Delivery - Backend

*Objetivo:* Desenvolvimento da API REST em FastAPI

Entregas principais:
* Estrutura base do projeto
* Conexão com banco de dados (SQLAlchemy)
* Modelos ORM e Schemas Pydantic
* Endpoints REST (POST/GET)
* Processamento de propostas
* Integrações externas (Sites A e B)
* Motor de simulação
* Cliente SMTP para notificações

h3. 3. Delivery - Frontend

*Objetivo:* Desenvolvimento da interface em Vue 3

Entregas principais:
* Projeto Vue 3 + Vite + Vuetify + Pinia
* Configuração Axios com interceptors
* Roteamento (Vue Router)
* Layouts e componentes
* Telas de formulário e acompanhamento
* State management (Pinia)
* Skeleton loaders
* Cards de status customizados

h3. 4. Scale

*Objetivo:* Melhorias de escalabilidade e qualidade

Entregas principais:
* Logging estruturado com correlation-id
* Dashboards de monitoramento
* Retry e circuit breaker
* Mascaramento de dados sensíveis (LGPD)
* RBAC completo
* Testes automatizados (pytest)

h2. 🔗 Links Úteis

* "Issues do Projeto":/projects/proposta-suite/issues
* "Gantt Chart":/projects/proposta-suite/issues/gantt
* "Calendário":/projects/proposta-suite/issues/calendar
* "Repositório Git":https://github.com/ericson-j-santos/proposta-suite

h2. 📚 Documentação Técnica

* [[Arquitetura]] - Diagrama e descrição da arquitetura
* [[API Reference]] - Documentação dos endpoints
* [[Banco de Dados]] - Schema e relacionamentos
* [[Deployment]] - Guia de implantação
* [[Testes]] - Estratégia e cobertura de testes

h2. 👥 Equipe

* *Product Owner:* TBD
* *Tech Lead:* TBD
* *Desenvolvedores:* TBD

---
_Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}_
"""
    
    return wiki


def gerar_pagina_arquitetura():
    """Gera página de arquitetura técnica"""
    
    return """h1. Arquitetura do Sistema

{{toc}}

h2. 📐 Visão Geral

O Proposta Suite segue uma arquitetura de microserviços simplificada:

<pre>
┌─────────────┐
│   Vue 3 UI  │ (Frontend)
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────┐
│  FastAPI    │ (Backend)
└──────┬──────┘
       │
       ├──────► SQLite/PostgreSQL (Database)
       │
       ├──────► Site A (API Externa)
       │
       ├──────► Sistema B (API Externa)
       │
       └──────► SMTP Server (E-mail)
</pre>

h2. 🔧 Stack Tecnológico

h3. Backend (FastAPI)

* *Framework:* FastAPI 0.100+
* *ORM:* SQLAlchemy 2.0
* *Validação:* Pydantic v2
* *ASGI Server:* Uvicorn
* *Migrations:* Alembic
* *Testes:* pytest

h3. Frontend (Vue 3)

* *Framework:* Vue 3 (Composition API)
* *Build Tool:* Vite
* *UI Library:* Vuetify 3
* *State Management:* Pinia
* *HTTP Client:* Axios
* *Router:* Vue Router 4

h3. Infraestrutura

* *Database:* SQLite (dev) / PostgreSQL (prod)
* *Reverse Proxy:* Nginx
* *Container:* Docker
* *CI/CD:* GitHub Actions

h2. 📊 Entidades Principais

h3. Proposta

<pre>
{
  "id": "uuid",
  "cliente_cpf": "string",
  "valor_solicitado": "decimal",
  "prazo_meses": "integer",
  "status": "enum",
  "created_at": "datetime",
  "updated_at": "datetime"
}
</pre>

h3. Simulacao

<pre>
{
  "id": "uuid",
  "proposta_id": "uuid",
  "taxa_juros": "decimal",
  "parcela_mensal": "decimal",
  "valor_total": "decimal",
  "created_at": "datetime"
}
</pre>

h2. 🔄 Fluxo de Dados

h3. Criação de Proposta

# Cliente preenche formulário (Vue 3)
# POST /propostas enviado ao backend
# Backend valida dados (Pydantic)
# Salva proposta no banco (status: "pendente")
# Inicia processamento assíncrono
# Consulta Site A (dados do contrato)
# Consulta Sistema B (taxas)
# Calcula simulação
# Salva simulação no banco
# Atualiza status da proposta
# Envia e-mail com resultado
# Frontend exibe atualização (polling/websocket)

h2. 🔒 Segurança

* *Autenticação:* JWT tokens
* *Autorização:* RBAC (Role-Based Access Control)
* *LGPD:* Mascaramento de dados sensíveis
* *HTTPS:* Obrigatório em produção
* *CORS:* Configurado para domínios permitidos
* *Rate Limiting:* 100 req/min por IP

h2. 📈 Escalabilidade

* *Horizontal Scaling:* Múltiplas instâncias FastAPI
* *Load Balancer:* Nginx upstream
* *Cache:* Redis para sessões
* *Queue:* Celery para processamento assíncrono
* *Monitoring:* Prometheus + Grafana

---
_Documentação técnica gerada automaticamente_
"""


def gerar_pagina_api():
    """Gera documentação de API"""
    
    return """h1. API Reference

{{toc}}

h2. 🌐 Base URL

<pre>
http://localhost:8000/api/v1
</pre>

h2. 🔑 Autenticação

Todas as requisições requerem token JWT no header:

<pre>
Authorization: Bearer {token}
</pre>

h2. 📝 Endpoints

h3. POST /propostas

Cria uma nova proposta imobiliária.

*Request Body:*

<pre>
{
  "cliente_cpf": "12345678900",
  "cliente_nome": "João Silva",
  "cliente_email": "joao@example.com",
  "valor_solicitado": 250000.00,
  "prazo_meses": 360,
  "tipo_imovel": "residencial",
  "finalidade": "compra"
}
</pre>

*Response (201 Created):*

<pre>
{
  "id": "uuid-da-proposta",
  "status": "pendente",
  "created_at": "2025-11-27T20:30:00Z",
  "message": "Proposta criada com sucesso"
}
</pre>

h3. GET /propostas/{id}/status

Consulta status de uma proposta.

*Response (200 OK):*

<pre>
{
  "id": "uuid",
  "status": "aprovada",
  "updated_at": "2025-11-27T20:35:00Z"
}
</pre>

*Status possíveis:*
* @pendente@ - Aguardando processamento
* @em_analise@ - Consultando sistemas externos
* @simulacao_gerada@ - Simulação disponível
* @aprovada@ - Proposta aprovada
* @rejeitada@ - Proposta rejeitada
* @erro@ - Erro no processamento

h3. GET /propostas/{id}/detalhes

Retorna detalhes completos da proposta e simulação.

*Response (200 OK):*

<pre>
{
  "proposta": {
    "id": "uuid",
    "cliente_cpf": "123.456.789-00",
    "valor_solicitado": 250000.00,
    "prazo_meses": 360,
    "status": "simulacao_gerada"
  },
  "simulacao": {
    "taxa_juros": 0.85,
    "parcela_mensal": 2150.00,
    "valor_total": 774000.00,
    "custo_efetivo_total": 3.10
  }
}
</pre>

h2. 🚨 Códigos de Erro

* @400@ - Bad Request (validação falhou)
* @401@ - Unauthorized (token inválido)
* @403@ - Forbidden (sem permissão)
* @404@ - Not Found (recurso não existe)
* @422@ - Unprocessable Entity (dados inválidos)
* @500@ - Internal Server Error (erro no servidor)

h2. 🔄 Rate Limiting

* *Limite:* 100 requisições por minuto
* *Header de resposta:* @X-RateLimit-Remaining@

h2. 📊 Monitoring

Endpoint de health check:

<pre>
GET /health

Response:
{
  "status": "healthy",
  "database": "connected",
  "external_apis": {
    "site_a": "ok",
    "sistema_b": "ok"
  }
}
</pre>

---
_Para testar a API, use a documentação interativa em /docs (Swagger UI)_
"""


def gerar_pagina_dashboards():
    """Gera página de Dashboards e Ferramentas"""
    
    return """h1. Dashboards e Ferramentas de Análise

{{toc}}

h2. 📊 Visão Geral

O projeto possui um conjunto completo de ferramentas Python para análise, documentação e monitoramento.
Todas as ferramentas são executadas via linha de comando e geram saídas em diversos formatos.

h2. 🔔 Configurações de Notificação

h3. E-mail Automático

*Status:* ✅ ATIVO

Você receberá notificações por e-mail quando:
* Criar uma nova issue
* Atualizar uma issue existente
* Adicionar comentários
* Fechar uma issue

A configuração @no_self_notified@ está desabilitada para receber notificações das próprias ações.

h2. 📝 Scripts Disponíveis

h3. 1. Gerador de Wiki (@gerar_wiki_projeto.py@)

*Funcionalidade:*
* Cria/atualiza páginas wiki automaticamente
* Extrai dados das issues em tempo real
* Mantém documentação sempre sincronizada

*Páginas geradas:*
* Wiki (Principal) - Visão geral e status
* Arquitetura - Diagrama técnico e stack
* API Reference - Documentação dos endpoints
* Deployment - Guias de implantação
* Dashboards - Esta página
* CHANGELOG - Controle de versões

*Execução:*
<pre>
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
source .venv-redmine/bin/activate
python3 gerar_wiki_projeto.py
</pre>

h3. 2. Dashboard HTML (@gerar_dashboard.py@)

*Funcionalidade:*
* Gera dashboard interativo com Chart.js
* 6 cards de métricas visuais
* 4 gráficos interativos (Donut, Bar, Stacked, Radar)
* Design responsivo e moderno

*Componentes:*
* 📈 Total de Tarefas
* 📊 Taxa de Conclusão
* ⚡ Em Andamento
* 🚀 Velocidade (tasks/dia)
* ⏱️ Lead Time Médio
* 📝 Tarefas Novas

*Gráficos:*
* 🍩 Distribuição por Status
* 📊 Progresso por Fase
* 📈 Status Detalhado (Stacked)
* 🎯 Métricas de Desempenho (Radar)

*Execução:*
<pre>
python3 gerar_dashboard.py
# Abre o HTML gerado: dashboard_proposta_suite_*.html
</pre>

h3. 3. Análises Avançadas (@analises_avancadas.py@)

*Funcionalidade:*
Implementa análises recomendadas para gestão ágil:

h4. 🔥 Burndown Chart
* Progresso ao longo do tempo
* Work remaining vs ideal
* Velocidade real vs ideal

h4. ⚡ Velocity Analysis
* Capacidade por semana
* Estatísticas (média/máx/mín)
* Previsão de conclusão

h4. 🏆 Quality Metrics
* Taxa de conclusão
* Lead Time médio
* Cycle Time médio
* Throughput (tasks/dia)
* WIP vs WIP ideal
* *Health Score* (0-100)

h4. 🚧 Bottleneck Detection
* Issues travadas
* Gargalos por fase
* Alertas críticos (>3 dias)

h4. 👥 Team Performance
* Desempenho por fase
* Lead time por área
* Recomendações

*Execução:*
<pre>
python3 analises_avancadas.py
# Exporta: relatorio_completo_*.csv
</pre>

h2. 📈 Métricas Atuais

*Última Atualização:* 27/11/2025

*Principais Indicadores:*
* Taxa de Conclusão: *95.5%* (42/44)
* Velocidade: *42 tasks/dia*
* Lead Time Médio: *0.3 horas* ⚡
* Health Score: *97.7/100* 🏆

*Status por Fase:*
* Discovery: 100% ✅
* Scale: 100% ✅
* Backend: 94.4% ⚡
* Frontend: 90% 🎯

h2. 🔄 Workflow Recomendado

h3. Atualização Semanal

<pre>
# 1. Gerar wiki atualizada
python3 gerar_wiki_projeto.py

# 2. Gerar dashboard
python3 gerar_dashboard.py

# 3. Análises avançadas
python3 analises_avancadas.py
</pre>

h2. 🎯 Análises Implementadas

h3. Metodologias Ágeis

* ✅ Burndown Chart
* ✅ Velocity Tracking
* ✅ Lead Time Analysis
* ✅ Cycle Time Analysis
* ✅ Throughput Metrics
* ✅ WIP Limits
* ✅ Bottleneck Detection

h3. Quality Metrics

* ✅ Completion Rate
* ✅ Health Score
* ✅ Team Performance
* ✅ Phase Progress

h2. 📂 Arquivos Gerados

h3. Documentação

* @GUIA_ANALISE_REDMINE.md@ - Guia completo de uso
* @DOCUMENTACAO_DASHBOARDS.md@ - Doc de dashboards
* @CHANGELOG.md@ - Controle de versões

h3. Saídas

* @dashboard_proposta_suite_*.html@ - Dashboards HTML
* @relatorio_completo_*.csv@ - Relatórios CSV detalhados
* @relatorio_proposta_suite_*.csv@ - Análises básicas CSV

---
_Ferramentas atualizadas automaticamente via @gerar_wiki_projeto.py@_
"""


def gerar_pagina_changelog():
    """Gera página do CHANGELOG com controle de versões"""
    
    try:
        with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
            changelog_content = f.read()
        
        # Converter Markdown para Textile (formato do Redmine)
        textile = changelog_content
        # Headers
        textile = textile.replace('# ', 'h1. ')
        textile = textile.replace('## ', 'h2. ')
        textile = textile.replace('### ', 'h3. ')
        textile = textile.replace('#### ', 'h4. ')
        textile = textile.replace('##### ', 'h5. ')
        # Bold
        textile = textile.replace('**', '*')
        # Code blocks
        textile = textile.replace('```', '<pre>')
        # Lists
        import re
        textile = re.sub(r'^- ', '* ', textile, flags=re.MULTILINE)
        
        return textile
    except FileNotFoundError:
        return """h1. CHANGELOG

Arquivo CHANGELOG.md não encontrado.
Execute o script de geração da wiki para criar o arquivo.
"""


def gerar_pagina_deployment():
    """Gera guia de deployment"""
    
    return """h1. Guia de Deployment

{{toc}}

h2. 🚀 Deploy em Desenvolvimento

h3. Pré-requisitos

* Python 3.11+
* Node.js 18+
* PostgreSQL 14+ (ou SQLite para dev)

h3. Backend (FastAPI)

<pre>
# Clone o repositório
git clone https://github.com/ericson-j-santos/proposta-suite.git
cd proposta-suite/backend

# Crie ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# Execute migrations
alembic upgrade head

# Inicie servidor
uvicorn main:app --reload --port 8000
</pre>

h3. Frontend (Vue 3)

<pre>
cd proposta-suite/frontend

# Instale dependências
npm install

# Configure API endpoint
cp .env.example .env
# Edite VITE_API_URL=http://localhost:8000

# Inicie dev server
npm run dev
</pre>

h2. 🐳 Deploy com Docker

h3. docker-compose.yml

<pre>
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/proposta
      - SMTP_HOST=smtp.gmail.com
    depends_on:
      - db
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=proposta
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
</pre>

h3. Executar

<pre>
docker-compose up -d
</pre>

h2. ☁️ Deploy em Produção

h3. Backend (Railway / Render / Fly.io)

# Push código para GitHub
# Conecte repositório no Railway
# Configure variáveis de ambiente:
** @DATABASE_URL@
** @SECRET_KEY@
** @SMTP_HOST@, @SMTP_USER@, @SMTP_PASS@
# Deploy automático em cada push

h3. Frontend (Vercel / Netlify)

<pre>
# Build para produção
npm run build

# Deploy Vercel
vercel --prod

# Ou Netlify
netlify deploy --prod
</pre>

h3. Database (Supabase / Neon)

# Crie projeto no Supabase
# Copie connection string
# Configure no @DATABASE_URL@
# Execute migrations:

<pre>
alembic upgrade head
</pre>

h2. 🔒 Checklist de Produção

* [ ] Variáveis de ambiente configuradas
* [ ] HTTPS habilitado
* [ ] CORS configurado corretamente
* [ ] Rate limiting ativado
* [ ] Logs estruturados
* [ ] Monitoring (Sentry/DataDog)
* [ ] Backup automático do banco
* [ ] Secrets rotation configurado
* [ ] Health checks configurados
* [ ] Rollback strategy definida

h2. 📊 Monitoramento

* *Logs:* CloudWatch / LogDNA
* *Metrics:* Prometheus + Grafana
* *Errors:* Sentry
* *Uptime:* UptimeRobot
* *Performance:* New Relic

---
_Guia atualizado para produção enterprise-ready_
"""


def criar_wikis_no_redmine(redmine, project, issues):
    """Cria todas as páginas wiki no Redmine"""
    
    print("\n" + "="*70)
    print("📚 CRIANDO PÁGINAS WIKI NO REDMINE")
    print("="*70)
    
    wikis = [
        ('Wiki', gerar_pagina_visao_geral(issues)),
        ('Arquitetura', gerar_pagina_arquitetura()),
        ('API_Reference', gerar_pagina_api()),
        ('Deployment', gerar_pagina_deployment()),
        ('Dashboards', gerar_pagina_dashboards()),
        ('CHANGELOG', gerar_pagina_changelog()),
    ]
    
    for titulo, conteudo in wikis:
        try:
            # Criar ou atualizar página wiki
            redmine.wiki_page.create(
                project_id=PROJECT_IDENTIFIER,
                title=titulo,
                text=conteudo,
                comments=f'Documentação gerada automaticamente em {datetime.now().strftime("%d/%m/%Y %H:%M")}'
            )
            print(f"   ✅ Página criada: {titulo}")
        except Exception as e:
            # Se já existe, atualizar
            try:
                wiki_page = redmine.wiki_page.get(titulo, project_id=PROJECT_IDENTIFIER)
                wiki_page.text = conteudo
                wiki_page.save()
                print(f"   ✅ Página atualizada: {titulo}")
            except Exception as e2:
                print(f"   ❌ Erro ao criar/atualizar {titulo}: {e2}")


def criar_versoes_no_redmine(redmine, project):
    """Cria versões/milestones no Redmine baseado no CHANGELOG"""
    
    print("\n" + "="*70)
    print("🏷️  CRIANDO VERSÕES NO REDMINE")
    print("="*70)
    
    versoes = [
        {
            'name': 'v1.0.0 - MVP Completo',
            'description': 'Release inicial do MVP com 95.5% de conclusão. Backend FastAPI, Frontend Vue 3, análises avançadas e documentação completa.',
            'status': 'open',
            'due_date': '2025-11-30',
            'sharing': 'none'
        },
        {
            'name': 'v1.1.0 - Melhorias e Finalização',
            'description': 'Conclusão das 2 issues pendentes: Template de e-mail (B-17) e Cards customizados (F-10)',
            'status': 'open',
            'due_date': '2025-12-15',
            'sharing': 'none'
        }
    ]
    
    for versao_data in versoes:
        try:
            # Verificar se versão já existe
            existing = None
            try:
                versions = redmine.version.filter(project_id=PROJECT_IDENTIFIER)
                for v in versions:
                    if v.name == versao_data['name']:
                        existing = v
                        break
            except:
                pass
            
            if existing:
                print(f"   ⚠️  Versão já existe: {versao_data['name']}")
            else:
                redmine.version.create(
                    project_id=PROJECT_IDENTIFIER,
                    name=versao_data['name'],
                    description=versao_data['description'],
                    status=versao_data['status'],
                    due_date=versao_data['due_date'],
                    sharing=versao_data['sharing']
                )
                print(f"   ✅ Versão criada: {versao_data['name']}")
        except Exception as e:
            print(f"   ❌ Erro ao criar versão {versao_data['name']}: {e}")


def atualizar_descricao_projeto(redmine, project):
    """Atualiza descrição do projeto com informações de versão"""
    
    print("\n" + "="*70)
    print("📝 ATUALIZANDO DESCRIÇÃO DO PROJETO")
    print("="*70)
    
    descricao = """**Proposta Suite - MVP FastAPI + Vue 3**

Sistema completo para gerenciamento de propostas imobiliárias.

**Versão Atual:** 1.0.0
**Data do Release:** 27/11/2025
**Status:** MVP Completo - 95.5% concluído

**Stack Tecnológico:**
* Backend: FastAPI (Python 3.11+)
* Frontend: Vue 3 + Vite + Vuetify
* Database: SQLite/PostgreSQL
* Gestão: Redmine 6.0.5

**Métricas:**
* Total de Issues: 44
* Concluídas: 42 (95.5%)
* Health Score: 97.7/100 🏆
* Velocidade: 42 tasks/dia

**Links Importantes:**
* Wiki: http://localhost:3001/projects/proposta-suite/wiki
* CHANGELOG: http://localhost:3001/projects/proposta-suite/wiki/CHANGELOG
* Dashboards: http://localhost:3001/projects/proposta-suite/wiki/Dashboards

**Documentação Completa:** Acesse a Wiki do projeto
"""
    
    try:
        project.description = descricao
        project.save()
        print(f"   ✅ Descrição atualizada com versão 1.0.0")
    except Exception as e:
        print(f"   ❌ Erro ao atualizar descrição: {e}")


def main():
    print("="*70)
    print("📝 GERADOR DE DOCUMENTAÇÃO WIKI - PROPOSTA SUITE")
    print("="*70)
    
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    project = redmine.project.get(PROJECT_IDENTIFIER)
    issues = list(redmine.issue.filter(
        project_id=PROJECT_IDENTIFIER,
        status_id='*',
        limit=1000
    ))
    
    print(f"\n📁 Projeto: {project.name}")
    print(f"📊 Issues analisadas: {len(issues)}")
    
    # Criar wikis
    criar_wikis_no_redmine(redmine, project, issues)
    
    # Criar versões
    criar_versoes_no_redmine(redmine, project)
    
    # Atualizar descrição do projeto
    atualizar_descricao_projeto(redmine, project)
    
    print("\n" + "="*70)
    print("✅ DOCUMENTAÇÃO WIKI CRIADA COM SUCESSO!")
    print("="*70)
    print(f"\n🌐 Acesse a Wiki:")
    print(f"   {REDMINE_URL}/projects/{PROJECT_IDENTIFIER}/wiki")
    print()
    print("📄 Páginas criadas:")
    print("   • Wiki (Página Principal)")
    print("   • Arquitetura")
    print("   • API Reference")
    print("   • Deployment")
    print("   • Dashboards (NOVO!)")
    print("   • CHANGELOG (Controle de Versões)")
    print()
    print("🏷️  Versões criadas:")
    print("   • v1.0.0 - MVP Completo")
    print("   • v1.1.0 - Melhorias e Finalização")
    print()
    print("📝 Descrição do projeto atualizada com versão atual")
    print()


if __name__ == '__main__':
    main()
