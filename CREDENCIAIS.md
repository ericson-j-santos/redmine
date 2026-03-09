# 🔐 CREDENCIAIS DE ACESSO - REDMINE

## 📝 Informações de Login

### Usuário Administrador Padrão

```
Login:    admin
Senha:    admin
Email:    admin@example.net
```

---

## 🌐 URL de Acesso

```
http://localhost:3001
```

---

## ⚠️ IMPORTANTE - SEGURANÇA

### Primeira Vez

Na primeira vez que fizer login, o Redmine **pode solicitar**:

1. Alteração da senha padrão
2. Atualização do email
3. Configuração de idioma

### Recomendações de Segurança

**Para ambiente de desenvolvimento:**

- ✅ As credenciais padrão são aceitáveis

**Para ambiente de produção:**

- ⚠️ **ALTERE IMEDIATAMENTE** a senha do admin
- ⚠️ Configure um email válido
- ⚠️ Crie usuários específicos para cada pessoa
- ⚠️ Não use a conta admin para uso diário

---

## 🚀 Como Alterar a Senha

1. Faça login com `admin` / `admin`
2. Clique em **"Minha conta"** (canto superior direito)
3. Clique em **"Alterar senha"**
4. Digite a nova senha duas vezes
5. Clique em **"Salvar"**

---

## 👥 Criar Novos Usuários

1. Faça login como admin
2. Vá em **Administração** → **Usuários**
3. Clique em **"Novo usuário"**
4. Preencha os dados
5. Defina as permissões
6. Clique em **"Criar"**

---

## 📋 Comandos Úteis

### Resetar senha do admin (emergência)

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
bundle exec rails runner "u = User.find_by(login: 'admin'); u.password = 'admin'; u.password_confirmation = 'admin'; u.save!"
```

### Listar todos os usuários

```bash
bundle exec rails runner "User.active.each { |u| puts \"#{u.login} - #{u.mail} - Admin: #{u.admin?}\" }"
```

### Criar novo admin

```bash
bundle exec rails runner "User.create!(login: 'seu_login', firstname: 'Seu', lastname: 'Nome', mail: 'seu@email.com', password: 'sua_senha', password_confirmation: 'sua_senha', admin: true, status: 1)"
```

---

## 🎯 Status do Usuário

- **1** = Ativo
- **2** = Registrado (aguardando aprovação)
- **3** = Bloqueado

---

**Data de criação:** 27/11/2025
