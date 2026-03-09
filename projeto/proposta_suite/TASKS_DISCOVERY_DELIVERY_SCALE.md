# Quadro de Tarefas – Discovery → Delivery → Scale

Legenda de status:
- ✅ Concluído
- 🔄 Em andamento
- ☐ Pendente

## Discovery

| ID   | Item                                             | Status |
|------|--------------------------------------------------|--------|
| D-01 | Objetivo da solução                              | ✅     |
| D-02 | Fluxo fim a fim (sequence diagram)              | ✅     |
| D-03 | Entidades principais                             | ✅     |
| D-04 | Integrações macro                                | ✅     |
| D-05 | Requisitos funcionais detalhados                 | ✅     |
| D-06 | Requisitos não funcionais                        | ✅     |
| D-07 | Dados pessoais sensíveis (LGPD)                  | ✅     |
| D-08 | Papéis (RBAC)                                   | ✅     |
| D-09 | Padrão correlation-id e logs estruturados        | ✅     |
| D-10 | Métricas principais                              | ✅     |

## Delivery – Backend

| ID   | Item                                             | Status |
|------|--------------------------------------------------|--------|
| B-01 | Estrutura base backend                           | ✅     |
| B-02 | main.py + middleware correlation-id              | ✅     |
| B-03 | Conexão banco (SQLAlchemy)                       | ✅     |
| B-04 | Modelos ORM Proposta/Simulacao                   | ✅     |
| B-05 | Schemas Pydantic                                 | ✅     |
| B-06 | POST /propostas                                  | ✅     |
| B-07 | GET /propostas/{id}/status                       | ✅     |
| B-08 | GET /propostas/{id}/detalhes                     | ✅     |
| B-09 | Validações de negócio adicionais                 | ✅     |
| B-10 | processar_proposta                               | ✅     |
| B-11 | Chamada Site A                                   | ✅     |
| B-12 | Chamada Sistema B                                | ✅     |
| B-13 | Motor de simulação                               | ✅     |
| B-14 | Persistir resultado simulação                    | ✅     |
| B-15 | Atualização de status                            | ✅     |
| B-16 | Cliente SMTP / e-mail                            | ✅     |
| B-17 | Template HTML e-mail                             | 🔄     |
| B-18 | Função enviar_email_simulacao                    | ✅     |

## Delivery – Frontend

| ID   | Item                                             | Status |
|------|--------------------------------------------------|--------|
| F-01 | Projeto Vue 3 + Vite + Vuetify + Pinia           | ✅     |
| F-02 | Axios + interceptor correlation-id               | ✅     |
| F-03 | Vue Router básico                                | ✅     |
| F-04 | Layout base (mínimo)                             | ✅     |
| F-05 | PropostaFormularioView                           | ✅     |
| F-06 | PropostaAcompanhamentoView                       | ✅     |
| F-07 | Store usePropostaStore                           | ✅     |
| F-08 | Skeleton no formulário                           | ✅     |
| F-09 | Skeleton no acompanhamento                       | ✅     |
| F-10 | Cards de status customizados                     | 🔄     |

## Scale – Observabilidade e Governança

| ID   | Item                                             | Status |
|------|--------------------------------------------------|--------|
| S-01 | Log estruturado com correlation-id               | ✅     |
| S-02 | Dashboard (Power BI / etc.)                      | ✅     |
| S-03 | Retry/circuit breaker chamadas externas          | ✅     |
| S-04 | Mascaramento de dados sensíveis                  | ✅     |
| S-05 | RBAC backend/frontend                            | ✅     |
| S-06 | Testes automatizados                             | ✅     |

