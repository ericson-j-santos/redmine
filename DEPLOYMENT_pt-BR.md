# Guia de Implantação do Redmine

## ⚠️ Importante: Problema de Compatibilidade com Vercel

**Esta instalação do Redmine está mostrando o erro "Página não encontrada" no Vercel porque o Vercel não foi projetado para hospedar aplicações tradicionais Ruby on Rails.**

### Por que não funciona no Vercel?

O Vercel é otimizado para:
- ✅ Sites estáticos (HTML, CSS, JavaScript)
- ✅ Aplicações Next.js, React, Vue
- ✅ Funções serverless (Node.js, Go, Python, Ruby)

O Redmine requer:
- ❌ Servidor de aplicação persistente (Puma, Unicorn)
- ❌ Servidor de banco de dados (MySQL, PostgreSQL, SQLite)
- ❌ Armazenamento de arquivos e jobs em background
- ❌ Processo Ruby de longa duração

## 🚀 Plataformas de Hospedagem Recomendadas

Aqui estão as melhores plataformas para implantar o Redmine:

### 1. **Heroku** (Mais Fácil)
Perfeito para aplicações Rails com planos gratuitos/pagos.

```bash
# Instalar Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login e criar app
heroku login
heroku create seu-redmine-app

# Adicionar banco de dados
heroku addons:create heroku-postgresql:mini

# Implantar
git push heroku master

# Executar migrações
heroku run rails db:migrate

# Visitar seu app
heroku open
```

**Prós:** Implantação simples, banco gerenciado, SSL automático
**Contras:** Planos pagos para uso em produção

### 2. **Railway** (Moderno e Simples)
Plataforma moderna com excelente suporte para Rails.

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login e implantar
railway login
railway init
railway up

# Visitar painel para configurar banco de dados
```

**Prós:** Ótima experiência do desenvolvedor, plano gratuito disponível
**Contras:** Plataforma relativamente nova

### 3. **Render** (Plano Gratuito Disponível)
Boa alternativa com plano gratuito.

1. Criar conta em [render.com](https://render.com)
2. Conectar repositório GitHub
3. Selecionar "Web Service"
4. Comando de Build: `bundle install; bundle exec rails db:migrate`
5. Comando de Start: `bundle exec rails server -b 0.0.0.0 -p $PORT`

**Prós:** Plano gratuito, implantações automáticas
**Contras:** Plano gratuito tem limitações

### 4. **Fly.io** (Implantação Global)
Ótimo para apps distribuídos.

```bash
# Instalar flyctl
curl -L https://fly.io/install.sh | sh

# Lançar app
fly launch

# Implantar
fly deploy

# Verificar status
fly status
```

**Prós:** Implantação global na edge, plano gratuito generoso
**Contras:** Requer alguma configuração

### 5. **DigitalOcean App Platform**
Plataforma gerenciada da DigitalOcean.

1. Criar conta DigitalOcean
2. Navegar para App Platform
3. Conectar repositório GitHub
4. Configurar comandos de build e execução
5. Implantar

**Prós:** Infraestrutura confiável, bom preço
**Contras:** Requer cartão de crédito

### 6. **VPS/Servidor Cloud** (Avançado)
Controle total com VPS (DigitalOcean, Linode, AWS EC2).

Requisitos:
- Ruby 3.2+
- Banco de dados (MySQL/PostgreSQL)
- Servidor web (Nginx/Apache)
- Servidor de aplicação (Puma)

**Prós:** Controle total, custo-efetivo para alto tráfego
**Contras:** Requer habilidades de gerenciamento de servidor

## 🔧 Configuração de Desenvolvimento Local

Para executar o Redmine localmente para desenvolvimento:

### Pré-requisitos
- Ruby 3.2.0 ou superior
- Bundler
- Banco de dados (SQLite para dev, MySQL/PostgreSQL para produção)
- Git

### Passos

1. **Clonar o repositório**
   ```bash
   git clone https://github.com/ericson-j-santos/redmine.git
   cd redmine
   ```

2. **Instalar dependências**
   ```bash
   bundle install
   ```

3. **Configurar banco de dados**
   ```bash
   # Copiar configuração de exemplo
   cp config/database.yml.example config/database.yml
   
   # Editar config/database.yml com suas configurações de banco
   ```

4. **Criar e migrar banco de dados**
   ```bash
   bundle exec rails db:create
   bundle exec rails db:migrate
   bundle exec rails redmine:load_default_data
   ```

5. **Iniciar o servidor**
   ```bash
   bundle exec rails server
   ```

6. **Acessar o Redmine**
   Abra seu navegador em: `http://localhost:3000`
   
   Credenciais padrão:
   - Usuário: `admin`
   - Senha: `admin`

## 🐳 Implantação com Docker

Use Docker para implantação containerizada:

```bash
# Usando imagem oficial do Redmine
docker run -d -p 3000:3000 \
  -e REDMINE_DB_MYSQL=db \
  -e REDMINE_DB_DATABASE=redmine \
  -e REDMINE_DB_USERNAME=redmine \
  -e REDMINE_DB_PASSWORD=secret \
  --name redmine \
  redmine:latest
```

Ou use Docker Compose - veja `docker-compose.yml` (se disponível).

## 📋 Checklist de Produção

Antes de implantar em produção:

- [ ] Definir `RAILS_ENV=production`
- [ ] Definir `SECRET_KEY_BASE` forte
- [ ] Configurar banco de dados de produção
- [ ] Configurar SSL/HTTPS
- [ ] Configurar entrega de email (SMTP)
- [ ] Configurar backups
- [ ] Configurar armazenamento de arquivos
- [ ] Configurar monitoramento
- [ ] Revisar configurações de segurança
- [ ] Testar todas as funcionalidades

## 🔐 Variáveis de Ambiente

Variáveis de ambiente necessárias para produção:

```bash
RAILS_ENV=production
SECRET_KEY_BASE=sua_chave_secreta_aqui
DATABASE_URL=postgresql://user:password@host:5432/redmine
REDMINE_DB_POSTGRES=host
REDMINE_DB_DATABASE=redmine
REDMINE_DB_USERNAME=redmine
REDMINE_DB_PASSWORD=password
```

Gerar uma chave secreta:
```bash
bundle exec rails secret
```

## 📚 Recursos Adicionais

- [Guia Oficial de Instalação do Redmine](https://www.redmine.org/projects/redmine/wiki/RedmineInstall)
- [Documentação do Redmine](https://www.redmine.org/projects/redmine/wiki/Guide)
- [Guia de Implantação Ruby on Rails](https://guides.rubyonrails.org/deployment.html)
- [Este Repositório](https://github.com/ericson-j-santos/redmine)

## 🆘 Solução de Problemas

### Erro "Página não encontrada" no Vercel
Isso é esperado. O Vercel não pode executar aplicações Rails sem configuração serverless complexa. Use uma das plataformas recomendadas acima.

### Erros de conexão com banco de dados
1. Verifique a configuração em `config/database.yml`
2. Certifique-se de que o servidor de banco está rodando
3. Verifique se as credenciais estão corretas
4. Verifique a conectividade de rede

### Assets não carregam
```bash
# Pré-compilar assets para produção
RAILS_ENV=production bundle exec rails assets:precompile
```

### Erros de migração
```bash
# Resetar banco de dados (ATENÇÃO: deleta todos os dados)
bundle exec rails db:reset

# Ou executar migrações manualmente
bundle exec rails db:migrate
```

## 📞 Obtendo Ajuda

- **GitHub Issues**: [Abrir uma issue](https://github.com/ericson-j-santos/redmine/issues)
- **Comunidade Redmine**: [Fóruns Redmine](https://www.redmine.org/projects/redmine/boards)
- **Stack Overflow**: Marque perguntas com `redmine` e `ruby-on-rails`

---

**Última Atualização**: Novembro 2025  
**Versão Redmine**: 6.0.x  
**Versão Rails**: 8.0.x  
**Versão Ruby**: 3.2.x
