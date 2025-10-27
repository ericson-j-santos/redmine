# Estratégia Completa de Testes - Redmine 6.0.5

## 📋 Visão Geral

Plano abrangente de testes para validar a funcionalidade completa da aplicação Redmine, com foco especial na feature de sorting por `spent_hours` e `total_spent_hours` implementada.

---

## 🎯 Objetivos de Testes

1. **Testes de Rotas (Routing)** - Validar que todos os endpoints estão mapeados corretamente
2. **Testes Funcionais (Functional)** - Testar controllers e lógica de negócio
3. **Testes de Integração (Integration)** - Testar fluxos end-to-end
4. **Testes de Sistema (System)** - Testar UI/UX e interações com o usuário
5. **Testes Unitários (Unit)** - Testar modelos e helpers
6. **Testes de API (API)** - Testar endpoints JSON/XML

---

## 📊 Estrutura de Testes Existente

```
test/
├── functional/                  # 66 arquivos - Testes de Controllers
│   ├── issues_controller_test.rb          # 8994 linhas - Testes principais
│   ├── issues_custom_fields_visibility_test.rb
│   └── [64 outros]
├── integration/                 # Testes de integração e routing
│   ├── routing/
│   │   └── issues_test.rb
│   ├── api_test/               # Testes da API REST
│   ├── issues_test.rb
│   └── [19 outros]
├── system/                      # 20+ arquivos - Testes com Capybara (UI/UX)
│   ├── issues_test.rb
│   ├── issues_reply_test.rb
│   ├── issues_import_test.rb
│   └── [17 outros]
├── unit/                        # Testes de modelos e helpers
│   ├── lib/
│   ├── models/
│   └── helpers/
├── fixtures/                    # Dados de teste
│   ├── issues.yml
│   ├── time_entries.yml
│   └── [múltiplos]
├── test_helper.rb              # Configuração principal de testes (510 linhas)
└── application_system_test_case.rb  # Configuração Capybara
```

---

## ✨ Feature: Sorting por Spent Hours

### Testes Já Implementados ✅

**Arquivo:** `test/functional/issues_controller_test.rb`

1. **test_index_sort_by_spent_hours** (linha 1328)

   - ✅ Verifica sorting crescente/decrescente por `spent_hours`
   - ✅ Valida ordem correta dos dados retornados

2. **test_index_sort_by_spent_hours_should_sort_by_visible_spent_hours** (linha 1335)

   - ✅ Testa visibilidade de horas por permissão de módulo
   - ✅ Valida que módulos desabilitados não aparecem

3. **test_index_sort_by_total_spent_hours** (linha 1360)

   - ✅ Verifica sorting correto por horas totais (incluindo subtarefas)
   - ✅ Valida agregação de horas

4. **test_index_sort_by_total_estimated_hours** (linha 1367)
   - ✅ Testa sorting por horas estimadas totais
   - ✅ Lida com valores nulos adequadamente

---

## 🔧 Testes a Implementar

### 1️⃣ TESTES DE ROTAS (Routing)

**Arquivo a criar:** `test/integration/routing/spent_hours_routes_test.rb`

```ruby
# Validar todos os endpoints relacionados a sorting
test_routing_issues_index_with_spent_hours_sort
test_routing_issues_index_with_total_spent_hours_sort
test_routing_issues_index_with_multiple_sort_params
test_routing_api_issues_with_spent_hours_sort
```

**Por quê:**

- Garantir que as rotas customizadas estão mapeadas corretamente
- Validar que query parameters são aceitos
- Testar encoding de rotas com múltiplos parâmetros

---

### 2️⃣ TESTES DE UX/UI (System Tests com Capybara)

**Arquivo a criar:** `test/system/spent_hours_sorting_ui_test.rb`

```ruby
# Testes com navegação real no navegador

test_issues_list_renders_spent_hours_column
  - Verificar que coluna "Spent Hours" aparece na tabela
  - Validar formatação (HH:MM)

test_issues_list_click_spent_hours_header_to_sort
  - Clicar no header "Spent Hours"
  - Verificar que lista é re-ordenada
  - Validar visual feedback (seta de sorting)

test_issues_list_sort_spent_hours_ascending_descending
  - Clicar 1x: Descendente (maior para menor)
  - Clicar 2x: Ascendente (menor para maior)
  - Validar mudança de icone/classe CSS

test_issues_list_total_spent_hours_displays_correctly
  - Verificar cálculo e exibição de horas totais
  - Incluir subtarefas na contagem visual

test_spent_hours_column_visible_only_with_permission
  - Login com user sem permissão
  - Coluna não deve aparecer
  - Login com user com permissão
  - Coluna deve aparecer

test_spent_hours_values_accurate_on_page
  - Verificar que valores na tela correspondem ao DB
  - Testar com TimeEntry data modificada
```

---

### 3️⃣ TESTES DE INTEGRAÇÃO (Integration Tests)

**Arquivo a expandir:** `test/integration/routing/issues_test.rb`

```ruby
# Testes de fluxo completo

test_issues_index_get_with_sort_by_spent_hours
  - GET /issues?sort=spent_hours:desc
  - Validar response 200
  - Verificar que issues estão em ordem correta no response

test_issues_index_get_with_sort_by_total_spent_hours
  - GET /issues?sort=total_spent_hours:desc
  - Validar ordem de horas totais no JSON/HTML

test_issues_with_invalid_sort_parameter
  - GET /issues?sort=invalid_column:desc
  - Validar que aplicação não quebra
  - Validar fallback para sort padrão

test_issues_multiple_sort_parameters
  - GET /issues?sort=spent_hours:desc&sort=priority:asc
  - Validar comportamento com múltiplos sorts

test_issues_spent_hours_sort_with_filters
  - GET /issues?sort=spent_hours:desc&status_id=open&assignee_id=1
  - Validar que sort funciona com filtros
```

---

### 4️⃣ TESTES DE API REST

**Arquivo a expandir:** `test/integration/api_test/issues_test.rb`

```ruby
# Testes de endpoints JSON/XML

test_api_get_issues_json_sorted_by_spent_hours
  - GET /issues.json?sort=spent_hours:desc
  - Validar JSON structure
  - Verificar ordem correta no array

test_api_get_issues_xml_sorted_by_total_spent_hours
  - GET /issues.xml?sort=total_spent_hours:desc
  - Validar XML structure
  - Verificar formatação de horas

test_api_includes_spent_hours_in_response
  - Validar que campo 'spent_hours' está no response
  - Validar que campo 'total_spent_hours' está no response

test_api_spent_hours_with_pagination
  - GET /issues.json?sort=spent_hours:desc&limit=10&offset=0
  - Validar paginação funciona com sorting
```

---

### 5️⃣ TESTES DE MODELOS (Unit Tests)

**Arquivo a expandir:** `test/models/issue_test.rb`

```ruby
# Testes de lógica de negócio

test_issue_spent_hours_calculation
  - Criar TimeEntries
  - Validar que spent_hours é calculado corretamente
  - Testar com diferentes valores

test_issue_total_spent_hours_includes_subtasks
  - Criar issue com subtasks
  - Verificar que total_spent_hours inclui todas
  - Testar com multiplos níveis

test_issue_spent_hours_respects_visibility
  - Criar TimeEntries com diferentes permissões
  - Validar que spent_hours mostra apenas visíveis
  - Testar com módulos habilitados/desabilitados

test_issue_spent_hours_ordering
  - Criar múltiplas issues com diferentes spent_hours
  - Validar que Issue.order(:spent_hours) funciona
```

---

## 🚀 Execução de Testes

### Executar Tudo

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
export PATH="$HOME/.rbenv/bin:$PATH" && eval "$(rbenv init -)"

# Todos os testes
bundle exec rails test

# Com cobertura
bundle exec rails test --coverage
```

### Executar por Categoria

```bash
# Apenas testes funcionais (mais rápido)
bundle exec rails test test/functional

# Apenas testes de sistema (UI, com Capybara/browser)
bundle exec rails test test/system

# Apenas testes de routing
bundle exec rails test test/integration/routing

# Apenas API
bundle exec rails test test/integration/api_test

# Apenas modelos
bundle exec rails test test/unit

# Apenas testes de issues
bundle exec rails test test/functional/issues_controller_test.rb

# Apenas spent_hours tests
bundle exec rails test test/functional/issues_controller_test.rb -n test_index_sort_by_spent_hours
```

### Executar com Verbosidade

```bash
# Mostrar todos os testes e resultados
bundle exec rails test -v

# Mostrar testes com seed para reproduzibilidade
bundle exec rails test --seed 12345

# Mostrar testes com profile (slowest tests)
bundle exec rails test --profile
```

---

## 📈 Cobertura de Testes

### Métricas Alvo

| Tipo                | Alvo  | Status     |
| ------------------- | ----- | ---------- |
| **Line Coverage**   | > 80% | 📊 A medir |
| **Branch Coverage** | > 75% | 📊 A medir |
| **Method Coverage** | > 85% | 📊 A medir |

### Gerar Relatório de Cobertura

```bash
# Com SimpleCov
COVERAGE=true bundle exec rails test

# Abrir relatório
open coverage/index.html
```

---

## ✅ Checklist de Testes Essenciais

### Fase 1: Funcional (Já Completo ✅)

- [x] test_index_sort_by_spent_hours
- [x] test_index_sort_by_spent_hours_should_sort_by_visible_spent_hours
- [x] test_index_sort_by_total_spent_hours
- [x] test_index_sort_by_total_estimated_hours

### Fase 2: Routing (A Implementar)

- [ ] test_routing_spent_hours_sorting_endpoints
- [ ] test_routing_total_spent_hours_endpoints
- [ ] test_routing_with_invalid_params

### Fase 3: Sistema / UI (A Implementar)

- [ ] test_spent_hours_column_visibility
- [ ] test_spent_hours_sorting_click_header
- [ ] test_spent_hours_ascending_descending_toggle
- [ ] test_total_spent_hours_display
- [ ] test_spent_hours_column_permission_based

### Fase 4: Integração (A Implementar)

- [ ] test_full_workflow_with_sorting
- [ ] test_sorting_with_filters
- [ ] test_sorting_with_pagination

### Fase 5: API (A Implementar)

- [ ] test_api_json_with_sorting
- [ ] test_api_xml_with_sorting
- [ ] test_api_response_structure

---

## 🛠️ Fixtures e Dados de Teste

### TimeEntry Fixtures

```yaml
# test/fixtures/time_entries.yml
time_entry_1:
  issue_id: 1
  user_id: 1
  hours: 2.5
  spent_on: 2025-10-01

time_entry_2:
  issue_id: 1
  user_id: 2
  hours: 3.0
  spent_on: 2025-10-02
```

### Issues Fixtures

```yaml
# test/fixtures/issues.yml
issue_1:
  project_id: 1
  subject: Issue with spent hours
  tracker_id: 1
  status_id: 1
  assigned_to_id: 1
```

---

## 📚 Referências

### Documentação Redmine

- [Redmine Test Helper](https://www.redmine.org/projects/redmine/wiki/Testing)
- [Rails Testing Guide](https://guides.rubyonrails.org/testing.html)

### Gems de Teste

- **minitest** - Framework padrão do Rails
- **capybara** - Testes de navegação (system tests)
- **selenium-webdriver** - Driver para Capybara
- **mocha** - Mocking e stubbing
- **simplecov** - Cobertura de código

### Estrutura de Testes no Redmine

- `test_helper.rb` - Configuração global (510 linhas)
- `application_system_test_case.rb` - Setup Capybara
- `object_helpers.rb` - Helpers customizados

---

## 🎓 Exemplo: Estrutura de um Test

### Functional Test (Controller)

```ruby
def test_index_sort_by_spent_hours
  get(:index, :params => {:sort => 'spent_hours:desc'})
  assert_response :success
  hours = issues_in_list.map(&:spent_hours)
  assert_equal hours.sort.reverse, hours
end
```

### System Test (UI)

```ruby
def test_spent_hours_column_visible_on_issues_list
  visit '/issues'
  assert_selector 'th', text: 'Spent Hours'
  assert_selector 'td', text: '2:30'
end
```

### Integration / Routing Test

```ruby
def test_route_issues_with_spent_hours_sort
  assert_routing(
    '/issues?sort=spent_hours:desc',
    controller: 'issues',
    action: 'index',
    sort: 'spent_hours:desc'
  )
end
```

---

## 📝 Próximos Passos

1. **Implementar Routing Tests** (30 min)

   - Criar `test/integration/routing/spent_hours_routes_test.rb`
   - Validar todos os endpoints

2. **Implementar System Tests** (1-2 horas)

   - Criar `test/system/spent_hours_sorting_ui_test.rb`
   - Testar interações de UI

3. **Executar Suite Completa** (20-30 min)

   - `bundle exec rails test`
   - Validar cobertura
   - Gerar relatórios

4. **Documentar Resultados**
   - Criar `TEST_RESULTS.md`
   - Incluir métricas de cobertura
   - Listar testes com status

---

## 📞 Contato

Para dúvidas sobre testes:

- Conferir `test/test_helper.rb` para helpers disponíveis
- Verificar testes similares em `test/functional/` como referência
- Rodar testes com `-v` para verbosidade

---

**Última Atualização:** 27 de outubro de 2025
**Versão Redmine:** 6.0.5
**Ruby Version:** 3.2.3
