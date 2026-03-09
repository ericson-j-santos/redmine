#!/usr/bin/env ruby
# Criar documentos no Redmine via Rails

project = Project.find_by_identifier('proposta-suite')

documentos = [
  {
    title: 'Guia de Configuração e Setup',
    description: <<~DESC,
      h1. Guia de Configuração Inicial

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
    DESC
    category_id: 6  # Documentação do usuário
  },
  {
    title: 'Arquitetura e Stack Técnico',
    description: <<~DESC,
      h1. Arquitetura do Sistema

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
    DESC
    category_id: 7  # Documentação técnica
  },
  {
    title: 'Métricas e Health Score',
    description: <<~DESC,
      h1. Métricas do Projeto

      h2. Status Atual (28/11/2025)

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
    DESC
    category_id: 7
  },
  {
    title: 'API Reference',
    description: <<~DESC,
      h1. API Reference

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
    DESC
    category_id: 7
  }
]

documentos.each do |doc|
  # Verifica se já existe
  existing = Document.where(project_id: project.id, title: doc[:title]).first

  if existing
    puts "⏭️  Já existe: #{doc[:title]}"
  else
    # Cria documento
    document = Document.new(
      project: project,
      title: doc[:title],
      description: doc[:description],
      category_id: doc[:category_id]
    )

    if document.save
      puts "✅ Criado: #{doc[:title]}"
    else
      puts "❌ Erro ao criar #{doc[:title]}: #{document.errors.full_messages.join(', ')}"
    end
  end
rescue => e
  puts "❌ Exceção: #{doc[:title]} - #{e.message}"
end

puts "\n✅ Documentos processados!"
puts "🌐 Acesse: http://localhost:3001/projects/proposta-suite/documents"
