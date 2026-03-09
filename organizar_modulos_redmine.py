#!/usr/bin/env python3
"""
Organiza documentos, arquivos e notícias no Redmine
"""

from redminelib import Redmine
import os
from datetime import datetime

# Configuração
REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'
PROJECT_ID = 'proposta-suite'

def criar_documentos(redmine, project):
    """Cria documentos na aba Documentos do Redmine"""
    
    print("\n" + "=" * 70)
    print("📄 CRIANDO DOCUMENTOS NO REDMINE")
    print("=" * 70)
    
    documentos = [
        {
            'title': 'Guia de Configuração e Setup',
            'description': '''h1. Guia de Configuração Inicial

h2. Pré-requisitos

* Python 3.10+
* Node.js 18+
* PostgreSQL 14+ (produção) ou SQLite (desenvolvimento)

h2. Backend - FastAPI

<pre>
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload
</pre>

h2. Frontend - Vue 3

<pre>
cd frontend
npm install
npm run dev
</pre>

h2. Variáveis de Ambiente

*Backend (.env):*
<pre>
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=sua-chave-secreta-aqui
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
</pre>

*Frontend (.env):*
<pre>
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=Proposta Suite
</pre>

h2. Verificação

* Backend: http://localhost:8000/docs
* Frontend: http://localhost:5173
* Health Check: http://localhost:8000/health
''',
            'category_id': 1  # Categoria "User documentation"
        },
        {
            'title': 'Arquitetura e Stack Técnico',
            'description': '''h1. Arquitetura do Sistema

h2. Backend - FastAPI

*Stack Principal:*
* FastAPI 0.104+
* SQLAlchemy 2.0+ (ORM)
* Pydantic v2 (validação)
* Alembic (migrations)
* JWT (autenticação)

*Estrutura:*
<pre>
backend/
├── app/
│   ├── api/        # Routers/endpoints
│   ├── core/       # Config, segurança
│   ├── models/     # SQLAlchemy models
│   ├── schemas/    # Pydantic schemas
│   └── services/   # Lógica de negócio
└── tests/
</pre>

h2. Frontend - Vue 3

*Stack Principal:*
* Vue 3 (Composition API)
* Vite 5+ (build)
* Vuetify 3 (UI)
* Pinia (state)
* Vue Router 4

*Estrutura:*
<pre>
frontend/
├── src/
│   ├── components/  # Componentes reutilizáveis
│   ├── views/       # Páginas
│   ├── stores/      # Pinia stores
│   ├── router/      # Rotas
│   └── composables/ # Lógica compartilhada
└── tests/
</pre>

h2. Segurança

* JWT com refresh tokens
* RBAC (Role-Based Access Control)
* CORS configurado
* HTTPS em produção
* Sanitização de inputs
* LGPD compliance
''',
            'category_id': 2  # Categoria "Technical documentation"
        },
        {
            'title': 'Métricas e Health Score do Projeto',
            'description': f'''h1. Métricas do Projeto

h2. Status Atual ({datetime.now().strftime('%d/%m/%Y')})

*Conclusão Geral:* 95.5% (42/44 issues)

*Por Fase:*
* Discovery: 100% (10/10)
* Backend: 94% (17/18)
* Frontend: 90% (9/10)
* Scale: 100% (6/6)

h2. Health Score: 97.7/100

*Componentes:*
* Taxa de Conclusão: 95.5% → 95.5 pontos
* Lead Time: 0.3h (excelente) → 100 pontos
* WIP: 2 tasks (leve sobrecarga) → -5 pontos

*Classificação:* ✅ EXCELENTE

h2. Velocity

*Média:* 42 tasks/dia
*Throughput:* 42.00 tasks/dia
*Previsão de conclusão:* 28/11/2025

h2. Issues Pendentes

# F-10 - Cards de status customizados na UI
# B-17 - Template HTML de e-mail da simulação

h2. Ferramentas de Análise

Acesse a página [[Dashboards]] para visualizar:
* Dashboard HTML interativo (Chart.js)
* Análises avançadas (burndown, velocity, quality)
* Relatórios em CSV
''',
            'category_id': 2
        },
        {
            'title': 'API Reference - Endpoints Principais',
            'description': '''h1. API Reference

h2. Autenticação

h3. POST /api/v1/auth/login

*Request:*
<pre>
{
  "username": "user@example.com",
  "password": "senha123"
}
</pre>

*Response:*
<pre>
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
</pre>

h2. Propostas

h3. GET /api/v1/propostas

*Query Params:*
* @skip@: offset (padrão: 0)
* @limit@: limite (padrão: 10, max: 100)
* @status@: filtro por status

*Response:*
<pre>
{
  "items": [...],
  "total": 100,
  "skip": 0,
  "limit": 10
}
</pre>

h3. POST /api/v1/propostas

*Request:*
<pre>
{
  "cliente_nome": "Empresa XYZ",
  "valor": 150000.00,
  "status": "rascunho"
}
</pre>

h2. Simulações

h3. POST /api/v1/simulacoes

Simula cálculos financeiros.

*Request:*
<pre>
{
  "valor_principal": 100000,
  "taxa_juros": 1.5,
  "prazo_meses": 12
}
</pre>

h2. Documentação Completa

* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc
''',
            'category_id': 2
        }
    ]
    
    for doc in documentos:
        try:
            # Verifica se documento já existe
            existing = redmine.document.filter(project_id=PROJECT_ID)
            if any(d.title == doc['title'] for d in existing):
                print(f"   ⏭️  Documento já existe: {doc['title']}")
                continue
            
            # Cria documento
            documento = redmine.document.create(
                project_id=PROJECT_ID,
                title=doc['title'],
                description=doc['description'],
                category_id=doc.get('category_id', 1)
            )
            print(f"   ✅ Documento criado: {doc['title']}")
            
        except Exception as e:
            print(f"   ⚠️  Erro ao criar '{doc['title']}': {e}")


def criar_noticias(redmine, project):
    """Cria notícias na página inicial do projeto"""
    
    print("\n" + "=" * 70)
    print("📰 CRIANDO NOTÍCIAS NO REDMINE")
    print("=" * 70)
    
    noticias = [
        {
            'title': '🎉 Release v1.0.0 - MVP Completo',
            'summary': 'Primeira versão do MVP está disponível com 95.5% de conclusão!',
            'description': '''h1. Release v1.0.0 - MVP Completo

*Data:* 27/11/2025

h2. Destaques

✅ *42 issues concluídas* (95.5% do total)
✅ *Health Score:* 97.7/100 - Excelente
✅ *Backend FastAPI* completamente funcional
✅ *Frontend Vue 3* com UI responsiva
✅ *Documentação completa* gerada automaticamente

h2. Funcionalidades Principais

*Backend:*
* API REST com autenticação JWT
* CRUD completo de propostas
* Sistema de simulações financeiras
* Validação com Pydantic
* Migrations automáticas

*Frontend:*
* Dashboard interativo
* Formulários dinâmicos
* Vuetify 3 UI
* State management com Pinia
* Roteamento otimizado

h2. Métricas

* Velocity: 42 tasks/dia
* Lead Time: 0.3 horas
* Throughput: Excelente

h2. Próximos Passos

Versão v1.1.0 prevista para 15/12/2025:
* F-10 - Cards de status customizados
* B-17 - Template HTML de e-mail

h2. Links

* [[Wiki]] - Documentação principal
* [[Dashboards]] - Métricas e análises
* [[CHANGELOG]] - Histórico completo
'''
        },
        {
            'title': '📊 Dashboards e Análises Disponíveis',
            'summary': 'Ferramentas de análise e monitoramento implementadas',
            'description': '''h1. Ferramentas de Análise Implementadas

*Data:* 27/11/2025

h2. Novidades

Implementamos um conjunto completo de ferramentas Python para análise do projeto:

h3. 1. Dashboard HTML Interativo

* Gráficos interativos com Chart.js
* Métricas em tempo real
* Visualização por fase
* Exportação de dados

h3. 2. Análises Avançadas

* *Burndown:* Acompanhamento vs planejado
* *Velocity:* Previsão de conclusão
* *Quality Metrics:* Health Score detalhado
* *Bottlenecks:* Identificação de gargalos
* *Team Performance:* Análise por fase

h3. 3. Geração Automática de Wiki

* Atualização automática de páginas
* Sincronização com issues
* Documentação sempre atual

h2. Como Usar

Todos os scripts estão em @/TEMP/CODIGOS/redmine-6.0.5/@:

<pre>
# Gerar dashboard
python3 gerar_dashboard.py

# Análises avançadas
python3 analises_avancadas.py

# Atualizar wiki
python3 gerar_wiki_projeto.py
</pre>

h2. Documentação

Acesse [[Dashboards]] para guia completo.
'''
        },
        {
            'title': '🔧 Configuração de E-mail e Notificações',
            'summary': 'Sistema de notificações por e-mail configurado e ativo',
            'description': '''h1. Sistema de Notificações Configurado

*Data:* 27/11/2025

h2. E-mail Automático Ativo

O sistema de notificações por e-mail está configurado e funcionando:

*SMTP:* Gmail
*Status:* ✅ Operacional
*Auto-notificação:* Habilitada

h2. Você Receberá E-mails Quando

* Criar uma nova issue
* Atualizar uma issue existente
* Adicionar comentários
* Fechar uma issue
* For mencionado em comentários
* For atribuído a uma tarefa

h2. Configuração Técnica

<pre>
# Redmine Configuration
default:
  email_delivery:
    delivery_method: :smtp
    smtp_settings:
      address: smtp.gmail.com
      port: 587
      domain: gmail.com
      authentication: :login
      user_name: ericsonjosedossantos@gmail.com
      enable_starttls_auto: true
</pre>

h2. Preferências do Usuário

*E-mail cadastrado:* ericsonjosedossantos@tieri659.onmicrosoft.com
*Notificações próprias:* Ativas
*Formato:* HTML

h2. Teste

Para testar, use:
<pre>
python3 testar_email.py
</pre>
'''
        }
    ]
    
    for noticia in noticias:
        try:
            # Verifica se notícia já existe
            existing = redmine.news.filter(project_id=PROJECT_ID)
            if any(n.title == noticia['title'] for n in existing):
                print(f"   ⏭️  Notícia já existe: {noticia['title']}")
                continue
            
            # Cria notícia
            news = redmine.news.create(
                project_id=PROJECT_ID,
                title=noticia['title'],
                summary=noticia['summary'],
                description=noticia['description']
            )
            print(f"   ✅ Notícia criada: {noticia['title']}")
            
        except Exception as e:
            print(f"   ⚠️  Erro ao criar '{noticia['title']}': {e}")


def upload_arquivos(redmine, project):
    """Faz upload de arquivos importantes para o Redmine"""
    
    print("\n" + "=" * 70)
    print("📎 PREPARANDO ARQUIVOS PARA UPLOAD")
    print("=" * 70)
    
    # Lista de arquivos para upload
    arquivos_info = [
        {
            'caminho': 'CHANGELOG.md',
            'descricao': 'Histórico de versões do projeto'
        },
        {
            'caminho': 'DOCUMENTACAO_DASHBOARDS.md',
            'descricao': 'Documentação completa das ferramentas de análise'
        }
    ]
    
    # Nota: A API python-redmine tem limitações para upload de arquivos
    # Vamos criar um documento listando os arquivos disponíveis
    
    arquivos_disponiveis = '''h1. Arquivos do Projeto

h2. Documentação

*CHANGELOG.md*
* Histórico completo de versões
* Formato: Keep a Changelog
* Localização: @/TEMP/CODIGOS/redmine-6.0.5/CHANGELOG.md@

*DOCUMENTACAO_DASHBOARDS.md*
* Guia completo de dashboards e análises
* Todas as ferramentas documentadas
* Localização: @/TEMP/CODIGOS/redmine-6.0.5/DOCUMENTACAO_DASHBOARDS.md@

h2. Scripts Python

*gerar_wiki_projeto.py*
* Gera/atualiza páginas wiki automaticamente
* 6 páginas: Wiki, Arquitetura, API, Deployment, Dashboards, CHANGELOG

*gerar_dashboard.py*
* Cria dashboard HTML interativo
* Charts: Doughnut, Bar, Stacked Bar, Radar
* Saída: @dashboard_proposta_suite_*.html@

*analises_avancadas.py*
* Análises: Burndown, Velocity, Quality, Bottlenecks
* Exporta CSV completo
* Health Score detalhado

*atualizar_status.py*
* Atualiza status de issues via API
* Gerenciamento de workflow

*analise_proposta_suite.py*
* Análise visual de issues
* Gráficos e estatísticas

*testar_email.py*
* Teste de configuração SMTP
* Validação de notificações

h2. Dashboards Gerados

Os dashboards HTML são gerados em:
@/TEMP/CODIGOS/redmine-6.0.5/dashboard_proposta_suite_*.html@

Abra no navegador para visualização interativa.

h2. Relatórios CSV

Relatórios exportados em:
@/TEMP/CODIGOS/redmine-6.0.5/relatorio_completo_*.csv@

Compatível com Excel, Google Sheets, etc.
'''
    
    try:
        doc = redmine.document.create(
            project_id=PROJECT_ID,
            title='Índice de Arquivos do Projeto',
            description=arquivos_disponiveis,
            category_id=2
        )
        print(f"   ✅ Documento de arquivos criado")
    except Exception as e:
        print(f"   ⚠️  Erro: {e}")


def main():
    """Função principal"""
    
    print("\n" + "=" * 70)
    print("🗂️  ORGANIZADOR DE MÓDULOS REDMINE")
    print("=" * 70)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🔗 URL: {REDMINE_URL}")
    print(f"📁 Projeto: {PROJECT_ID}")
    
    # Conecta ao Redmine
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    project = redmine.project.get(PROJECT_ID)
    
    # Executa operações
    criar_documentos(redmine, project)
    criar_noticias(redmine, project)
    upload_arquivos(redmine, project)
    
    print("\n" + "=" * 70)
    print("✅ ORGANIZAÇÃO CONCLUÍDA!")
    print("=" * 70)
    print("\n🌐 Acesse:")
    print(f"   📄 Documentos: {REDMINE_URL}/projects/{PROJECT_ID}/documents")
    print(f"   📰 Notícias: {REDMINE_URL}/projects/{PROJECT_ID}/news")
    print(f"   📁 Arquivos: {REDMINE_URL}/projects/{PROJECT_ID}/files")
    print()


if __name__ == '__main__':
    main()
