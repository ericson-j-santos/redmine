# Changelog - Proposta Suite MVP

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Em Desenvolvimento

- F-10: Cards de status customizados na UI
- B-17: Template HTML de e-mail da simulação

## [1.0.0] - 2025-11-27

### 🎉 Release Inicial - MVP Completo

#### ✨ Adicionado

##### Discovery (100% Concluído)

- D-01: Objetivo da solução definido
- D-02: Fluxo completo da solução documentado
- D-03: Entidades e relacionamentos mapeados
- D-04: Integrações externas especificadas (Site A, Sistema B)
- D-05: Requisitos funcionais levantados
- D-06: Requisitos não funcionais definidos
- D-07: Definição de papéis e RBAC
- D-08: Logging estruturado especificado
- D-09: Monitoramento e métricas definidos
- D-10: Políticas de retry e circuit breaker

##### Backend - FastAPI (94% Concluído)

- B-01: Estrutura inicial do projeto FastAPI
- B-02: Conexão com banco de dados SQLite/PostgreSQL (SQLAlchemy)
- B-03: Modelos ORM para Proposta, Cliente, Simulação
- B-04: Schemas Pydantic para validação
- B-05: Endpoint POST /propostas implementado
- B-06: Endpoint GET /propostas/{id}/status implementado
- B-07: Endpoint GET /propostas/{id}/detalhes implementado
- B-08: Processamento assíncrono de propostas
- B-09: Integração com Site A (mock/real)
- B-10: Integração com Sistema B (taxas)
- B-11: Motor de simulação de crédito
- B-12: Cliente SMTP para notificações
- B-13: Tratamento de erros e exceções
- B-14: Validações de negócio
- B-15: Estrutura de testes unitários (pytest)
- B-16: Documentação Swagger/OpenAPI automática
- **Pendente:** B-17 - Template HTML de e-mail da simulação

##### Frontend - Vue 3 (90% Concluído)

- F-01: Projeto Vue 3 + Vite + Vuetify criado
- F-02: Configuração do Axios com interceptors
- F-03: Roteamento configurado (Vue Router)
- F-04: Layout base da aplicação
- F-05: Componente de formulário de proposta
- F-06: Tela de acompanhamento de status
- F-07: State management (Pinia) configurado
- F-08: Integração com API backend
- F-09: Skeleton loaders durante carregamento
- **Pendente:** F-10 - Cards de status customizados na UI

##### Scale & Production (100% Concluído)

- S-01: Logging estruturado com correlation-id
- S-02: Dashboard de monitoramento básico
- S-03: Retry automático em integrações
- S-04: Circuit breaker implementado
- S-05: Mascaramento de dados sensíveis (LGPD)
- S-06: Testes automatizados (pytest) executando

##### Infraestrutura & DevOps

- Sistema de controle de versão (Git)
- Ambiente virtual Python configurado
- Dependências gerenciadas (requirements.txt / package.json)
- Redmine configurado para gestão de projeto
- API REST habilitada no Redmine
- Wiki técnica completa
- Dashboards de análise customizados

#### 📊 Ferramentas de Análise

##### Scripts Python

- `import_proposta_suite.py` - Importação de issues do CSV
- `atualizar_status.py` - Sincronização de status
- `analise_proposta_suite.py` - Análise básica do projeto
- `analises_avancadas.py` - Análises avançadas (Burndown, Velocity, Quality)
- `gerar_wiki_projeto.py` - Geração automática de Wiki
- `gerar_dashboard.py` - Dashboard HTML interativo
- `testar_email.py` - Teste de notificações

##### Documentação

- Wiki completa no Redmine (4 páginas)
- GUIA_ANALISE_REDMINE.md - Guia de uso completo
- DOCUMENTACAO_DASHBOARDS.md - Documentação de dashboards
- CHANGELOG.md - Este arquivo de controle de versões

#### 📈 Métricas do Release

- **Taxa de Conclusão:** 95.5% (42/44 issues)
- **Total de Issues:** 44
- **Issues Fechadas:** 42
- **Issues Pendentes:** 2
- **Velocidade Média:** 42 tasks/dia
- **Lead Time Médio:** 0.3 horas
- **Health Score:** 97.7/100 🏆

#### 🔧 Tecnologias Utilizadas

**Backend:**

- Python 3.11+
- FastAPI 0.100+
- SQLAlchemy 2.0
- Pydantic v2
- Uvicorn (ASGI server)
- pytest

**Frontend:**

- Vue 3 (Composition API)
- Vite
- Vuetify 3
- Pinia (state management)
- Axios
- Vue Router 4

**Infraestrutura:**

- SQLite (desenvolvimento)
- PostgreSQL (produção)
- Nginx (reverse proxy)
- Docker
- GitHub Actions (CI/CD)

**Gestão de Projeto:**

- Redmine 6.0.5
- Ruby 3.2.3
- Rails 8.0.3

#### 🔒 Segurança

- Autenticação JWT implementada
- RBAC (Role-Based Access Control)
- Mascaramento de dados sensíveis (LGPD)
- HTTPS configurado
- CORS configurado
- Rate limiting (100 req/min)

#### 📝 Documentação

- Swagger UI automático (/docs)
- ReDoc disponível (/redoc)
- Wiki técnica completa
- Guias de deployment
- Documentação de API

---

## [0.2.0] - 2025-11-27

### Adicionado

- Sistema de análises avançadas
- Dashboard HTML customizado com Chart.js
- Gerador automático de Wiki
- Controle de versões (CHANGELOG)

### Melhorado

- Notificações por e-mail (incluindo auto-notificações)
- Documentação técnica expandida
- Análises de qualidade (Health Score)

---

## [0.1.0] - 2025-11-27

### Adicionado

- Setup inicial do projeto Redmine
- Importação de 44 issues do CSV
- Configuração de trackers e status em português
- Scripts básicos de análise
- Configuração de SMTP

---

## Tipos de Mudanças

- **Adicionado** - para novas funcionalidades
- **Modificado** - para mudanças em funcionalidades existentes
- **Descontinuado** - para funcionalidades que serão removidas
- **Removido** - para funcionalidades removidas
- **Corrigido** - para correção de bugs
- **Segurança** - para vulnerabilidades corrigidas

---

## Versionamento

Este projeto segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/):

- **MAJOR** (X.0.0): Mudanças incompatíveis na API
- **MINOR** (1.X.0): Novas funcionalidades mantendo compatibilidade
- **PATCH** (1.0.X): Correções de bugs mantendo compatibilidade

**Versão Atual:** 1.0.0
**Data do Release:** 27/11/2025
**Status:** MVP Completo - Pronto para produção
