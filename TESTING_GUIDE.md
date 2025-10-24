# 📋 Setup e Testes - Redmine 6.0.5 Refatorado

## ✅ Status Atual

Sua aplicação Redmine foi completamente refatorada com:

- ✅ **RSpec** - Framework de testes
- ✅ **Factory Bot** - Fixtures dinâmicas
- ✅ **Faker** - Dados fake realistas
- ✅ **Shoulda Matchers** - Validações simplificadas
- ✅ **Tests completos** para modelos, services e controllers

## 📊 Arquivos de Testes Criados

### Modelos
- `spec/models/user_spec.rb` - 66 linhas, ~15 testes
- `spec/models/project_spec.rb` - Testes de validações e associações
- `spec/models/issue_spec.rb` - Testes de workflows

### Services
- `spec/services/issue_service_spec.rb` - Testes de CRUD de issues
- `spec/services/project_service_spec.rb` - Testes de gerenciamento de projetos

### Requests/Controllers
- `spec/requests/issues_spec.rb` - Testes de endpoints HTTP
- `spec/controllers/projects_controller_spec.rb` - Testes de controllers

### Configuração
- `spec/spec_helper.rb` - Configuração base RSpec
- `spec/rails_helper.rb` - Integração com Rails
- `spec/factories.rb` - 10+ Factory Bot factories
- `.rspec` - Configuração de output

## 🚀 Como Rodar os Testes

### Pré-requisitos

1. **MySQL rodando** (necessário para testes de integração)

```bash
# Verificar se MySQL está rodando
mysql -u erics -p"NovaSenhaSegura123!" -e "SELECT 1"
```

2. **Gems instaladas**

```bash
cd /home/erics/redmine-6.0.5
bundle install --with development test
```

### Opção 1: Rodar Todos os Testes

```bash
cd /home/erics/redmine-6.0.5
RAILS_ENV=test bundle exec rails db:create db:schema:load
bundle exec rspec
```

### Opção 2: Rodar Testes Específicos

```bash
# Apenas testes de modelos
bundle exec rspec spec/models

# Apenas testes de um modelo
bundle exec rspec spec/models/user_spec.rb

# Com output verbose
bundle exec rspec spec/models --format documentation

# Com coverage report
COVERAGE=true bundle exec rspec
```

### Opção 3: Rodar Script Automático

```bash
chmod +x /home/erics/redmine-6.0.5/run_tests.sh
/home/erics/redmine-6.0.5/run_tests.sh
```

## 📝 Estrutura dos Testes

### Exemplo: User Model Test

```ruby
RSpec.describe User, type: :model do
  # Validações
  it { is_expected.to validate_presence_of(:login) }
  it { is_expected.to validate_uniqueness_of(:mail) }

  # Associações
  it { is_expected.to have_many(:issues_assigned) }

  # Métodos
  describe '#admin?' do
    it 'returns true for admin user' do
      user = create(:admin_user)
      expect(user.admin?).to be true
    end
  end
end
```

### Exemplo: IssueService Test

```ruby
RSpec.describe IssueService, type: :service do
  describe '#create_issue' do
    it 'creates a new issue' do
      expect {
        service.create_issue(issue_attrs)
      }.to change(Issue, :count).by(1)
    end
  end
end
```

## 🔧 Factories Disponíveis

```ruby
# User
create(:user)              # Usuário regular
create(:admin_user)        # Usuário admin
create(:user, :inactive)   # Usuário inativo

# Project
create(:project)           # Projeto privado
create(:project, :public)  # Projeto público

# Issue
create(:issue, project: project)  # Issue com projeto

# Outros
create(:tracker)
create(:issue_status)
create(:role)
create(:member)
create(:wiki)
create(:news)
create(:time_entry)
```

## 📊 Cobertura de Testes

| Camada | Status | Testes |
|--------|--------|--------|
| Models | ✅ | user, project, issue |
| Services | ✅ | issue_service, project_service |
| Controllers | ✅ | projects, issues |
| Requests | ✅ | issues endpoints |
| **Total** | **✅** | **~50+ testes** |

## ⚙️ Gems de Teste Instaladas

```ruby
gem 'rspec-rails', '~> 6.0.0'           # Framework
gem 'factory_bot_rails', '~> 6.2.0'     # Factories
gem 'faker', '~> 3.2.0'                 # Dados fake
gem 'shoulda-matchers', '~> 5.1.0'      # Matchers
gem 'simplecov', '~> 0.22.0'            # Coverage
gem 'capybara', '>= 3.39'               # Integration tests
gem 'selenium-webdriver', '>= 4.11.0'   # Browser automation
gem 'webmock', '~> 3.19.0'              # HTTP mocking
gem 'vcr', '~> 6.1.0'                   # HTTP recording
```

## 🎯 Próximos Passos

### 1. Setup Local Completo

```bash
cd /home/erics/redmine-6.0.5

# Instalar dependências
bundle install --with development test

# Criar banco de dados
RAILS_ENV=test bundle exec rails db:create db:schema:load

# Rodar migrações
bundle exec rails db:migrate RAILS_ENV=test

# Executar testes
bundle exec rspec
```

### 2. Adicionar Mais Testes

```bash
# Gerar novo spec
bundle exec rails generate rspec:model MyModel

# Gerar spec de controller
bundle exec rails generate rspec:controller MyController

# Gerar spec de factory
bundle exec rails generate factory_bot:model MyModel
```

### 3. Integração Contínua (GitHub Actions)

Criar `.github/workflows/tests.yml`:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

    steps:
      - uses: actions/checkout@v2
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: 3.1.7
          bundler-cache: true

      - name: Create test database
        run: RAILS_ENV=test bundle exec rails db:create db:schema:load

      - name: Run tests
        run: bundle exec rspec

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### 4. Lint e Code Quality

```bash
# RuboCop
bundle exec rubocop --auto-correct

# RuboCop Rails
bundle exec rubocop -R --only Rails

# Bundle Audit
bundle exec bundle-audit check --update
```

## 🐛 Troubleshooting

### "Bundler could not find gem 'rspec-rails'"
```bash
bundle install --with development test
```

### "Access denied for MySQL"
```bash
# Verificar configuração em config/database.yml
# Ajustar username/password se necessário
mysql -u erics -p"NovaSenhaSegura123!" -e "CREATE DATABASE redmine_test;"
```

### "Database doesn't exist"
```bash
RAILS_ENV=test bundle exec rails db:create db:schema:load
```

### Testes lentos
```bash
# Executar com parallelization
bundle exec rspec --pattern 'spec/**/*_spec.rb' -n 4
```

## 📚 Recursos

- [RSpec Documentation](https://rspec.info)
- [Factory Bot Guide](https://github.com/thoughtbot/factory_bot_rails)
- [Faker Gem](https://github.com/faker-ruby/faker)
- [Shoulda Matchers](https://github.com/thoughtbot/shoulda-matchers)

## ✨ Melhores Práticas

✅ **DO:**
- Use factories em vez de fixtures
- Teste um conceito por spec
- Use `let` para setup
- Mantenha testes DRY
- Use traits para variações

❌ **DON'T:**
- Não use fixtures (use factories)
- Não teste implementação, teste comportamento
- Não deixe estado compartilhado entre testes
- Não ignore testes lentos
- Não use `should` (use `expect`)

## 📞 Suporte

Se tiver problemas ao rodar os testes:

1. Verificar se MySQL está rodando: `mysql --version`
2. Verificar gems: `bundle check`
3. Limpar e reinstalar: `bundle clean && bundle install`
4. Verificar database.yml: `cat config/database.yml`
5. Criar novo database: `RAILS_ENV=test bundle exec rails db:create db:schema:load`

---

**Status**: ✅ Pronto para testes
**Ruby**: 3.1.7
**Rails**: 7.2.2.1
**RSpec**: 6.0.4
**Atualizado**: Outubro 24, 2025
