# 📧 CONFIGURAÇÃO DE EMAIL - REDMINE

## ✅ Email Configurado com Sucesso!

### 🔧 Configuração Atual

**Servidor SMTP:** Gmail  
**Email Remetente:** ericson.takay@gmail.com  
**Porta:** 587 (TLS)  
**Autenticação:** Habilitada

---

## 📨 Tipos de Email que o Redmine Envia

### Automáticos

- ✉️ **Notificações de Issues** - Quando alguém cria/atualiza uma issue
- ✉️ **Atribuições** - Quando você é atribuído a uma tarefa
- ✉️ **Comentários** - Novos comentários em issues que você segue
- ✉️ **Mudanças de Status** - Quando status de issue muda
- ✉️ **Lembretes** - Tarefas com prazo próximo

### Sob Demanda

- 🔑 **Recuperação de Senha** - "Esqueci minha senha"
- 👤 **Novos Usuários** - Quando admin cria conta para alguém
- 📋 **Relatórios** - Relatórios agendados (se configurado)

---

## ⚙️ Configurar Notificações

### Para o Admin (você)

1. Faça login: http://localhost:3001
2. Clique em **"Minha conta"** (canto superior direito)
3. Vá na aba **"Configurações de Email"**
4. Configure:
   - ✅ **"Para eventos em todos os meus projetos"** - Receberá tudo
   - ⚙️ **Personalizar por tipo** - Escolher o que receber

### Para Novos Usuários

Ao criar usuário, marque:

- ✅ **"Enviar informações da conta para o usuário"**
- O usuário receberá email com login e senha temporária

---

## 🧪 Testar Envio de Email

### Método 1: Via Interface Web

1. Acesse: http://localhost:3001
2. Login: `admin` / `admin`
3. Vá em **Administração** → **Configurações** → **Notificações por email**
4. Configure:
   - Servidor SMTP: `smtp.gmail.com`
   - Porta: `587`
   - Email remetente: `ericson.takay@gmail.com`
5. Clique em **"Enviar email de teste"**
6. Digite: `ericsonjosedossantos@tieri659.onmicrosoft.com`
7. Clique em **"Enviar"**

### Método 2: Via Console Rails

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5

# Testar configuração SMTP
bundle exec rails runner '
  require "net/smtp"
  puts "Testando conexão SMTP..."
  smtp = Net::SMTP.new("smtp.gmail.com", 587)
  smtp.enable_starttls
  smtp.start("gmail.com", "ericson.takay@gmail.com", "ybstrodltteskwlx", :plain) do |s|
    puts "✅ Conexão SMTP OK!"
  end
'

# Enviar email de teste
bundle exec rails runner '
  puts "Enviando email de teste..."
  Mailer.test_email("ericsonjosedossantos@tieri659.onmicrosoft.com").deliver_now
  puts "✅ Email enviado!"
'
```

---

## 📋 Comandos Úteis

### Verificar Configuração de Email

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
bundle exec rails runner 'puts ActionMailer::Base.smtp_settings.inspect'
```

### Ver Emails na Fila (se houver)

```bash
bundle exec rails runner 'puts "Emails pendentes: #{ActionMailer::Base.deliveries.count}"'
```

### Limpar Fila de Emails

```bash
bundle exec rails runner 'ActionMailer::Base.deliveries.clear'
```

---

## ⚠️ Importante - Segurança

### Senha de App Gmail

A senha configurada (`ybstrodltteskwlx`) é uma **senha de aplicativo**, não sua senha real do Gmail.

**Para gerar nova senha de app:**

1. Acesse: https://myaccount.google.com/apppasswords
2. Selecione: "Outro (nome personalizado)"
3. Digite: "Redmine"
4. Copie a senha de 16 dígitos
5. Atualize em `config/configuration.yml`

### Proteção do Arquivo

```bash
# Proteger arquivo de configuração
chmod 600 /home/erics/TEMP/CODIGOS/redmine-6.0.5/config/configuration.yml

# Adicionar ao .gitignore (se usar git)
echo "config/configuration.yml" >> .gitignore
```

---

## 🔍 Troubleshooting

### Email não chega

1. **Verifique SPAM** no email de destino
2. **Aguarde até 2 minutos** (Gmail pode demorar)
3. **Verifique logs:**
   ```bash
   tail -f log/development.log
   ```

### Erro: "Authentication failed"

```bash
# Verificar se senha está correta
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
grep "password:" config/configuration.yml
```

**Solução:** Gere nova senha de app no Google

### Erro: "Connection timeout"

**Possíveis causas:**

- Firewall bloqueando porta 587
- Antivírus bloqueando SMTP
- Problemas de rede

**Teste manual:**

```bash
telnet smtp.gmail.com 587
```

---

## 📊 Monitorar Emails Enviados

### Ver Últimos Emails (se houver)

```bash
cd /home/erics/TEMP/CODIGOS/redmine-6.0.5
bundle exec rails runner '
  ActionMailer::Base.deliveries.last(5).each do |mail|
    puts "Para: #{mail.to}"
    puts "Assunto: #{mail.subject}"
    puts "---"
  end
'
```

---

## 🎯 Próximos Passos

1. ✅ **Configuração concluída** - Email já está funcionando
2. 🧪 **Testar** - Enviar email de teste
3. ⚙️ **Ajustar** - Configurar preferências de notificação
4. 📧 **Usar** - Criar issues e receber notificações automáticas

---

**Configuração criada em:** 27/11/2025  
**Baseada em:** Console Seguro (configuração testada e funcionando)
