# Proposta Suite – MVP (FastAPI + Vue 3)

MVP de cadastro, simulação e envio de proposta imobiliária.

## Backend (FastAPI)

- FastAPI com SQLite (async)
- Rotas principais:
  - `POST /api/propostas` – cria proposta e dispara processamento assíncrono
  - `GET /api/propostas/{id}/status` – acompanha status e resumo de simulação
  - `GET /api/propostas/{id}/detalhes` – detalhes completos (RBAC: gestor/admin)
- Serviços de integração (mock):
  - Site A (dados de contrato)
  - Sistema B (taxas)
  - Motor de simulação
  - Envio de e-mail (simulado)
- RBAC via header `X-User-Role` (`analista`, `gestor`, `admin`)
- Correlation ID (`x-correlation-id`) em middleware e logs
- Retry + circuit breaker nas chamadas externas
- Testes com `pytest` (motor de simulação e API)

### Como rodar o backend (exemplo Debian 12)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend (Vue 3 + Vuetify + Pinia)

- Formulário de cadastro de proposta
- Tela de acompanhamento com polling do status
- `v-skeleton-loader` em carregamentos
- Axios com:
  - `x-correlation-id` automático
  - `X-User-Role` (padrão: `analista`)
- Proxy Vite redirecionando `/api` para `http://localhost:8000`

### Como rodar o frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse: `http://localhost:5173`
