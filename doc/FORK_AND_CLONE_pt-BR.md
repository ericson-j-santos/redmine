# Como Clonar e Copiar Este Repositório

Este guia explica como fazer fork (cópia) deste repositório do Redmine para sua conta pessoal do GitHub e cloná-lo para sua máquina local.

## Passo 1: Fazer Fork do Repositório no GitHub

1. Acesse o repositório no GitHub: https://github.com/ericson-j-santos/redmine
2. Clique no botão **"Fork"** no canto superior direito da página
3. Selecione sua conta pessoal como destino do fork
4. Aguarde enquanto o GitHub cria uma cópia do repositório em sua conta

Após o fork, você terá sua própria cópia do repositório em `https://github.com/SEU-USUARIO/redmine`

## Passo 2: Clonar o Repositório para sua Máquina Local

Depois de fazer o fork, você pode clonar o repositório para sua máquina local:

```bash
# Clone o seu fork (substitua SEU-USUARIO pelo seu nome de usuário do GitHub)
git clone https://github.com/SEU-USUARIO/redmine.git

# Entre no diretório do repositório
cd redmine
```

## Passo 3: Configurar Remote Upstream (Opcional)

Para manter seu fork atualizado com o repositório original, configure o remote upstream:

```bash
# Adicione o repositório original como remote upstream
git remote add upstream https://github.com/ericson-j-santos/redmine.git

# Verifique os remotes configurados
git remote -v
```

Você verá algo assim:
```
origin    https://github.com/SEU-USUARIO/redmine.git (fetch)
origin    https://github.com/SEU-USUARIO/redmine.git (push)
upstream  https://github.com/ericson-j-santos/redmine.git (fetch)
upstream  https://github.com/ericson-j-santos/redmine.git (push)
```

## Passo 4: Sincronizar com o Repositório Original (Opcional)

Para atualizar seu fork com as últimas mudanças do repositório original:

```bash
# Busque as atualizações do upstream
git fetch upstream

# Certifique-se de estar na branch principal
git checkout main

# Faça merge das mudanças do upstream
git merge upstream/main

# Envie as atualizações para seu fork no GitHub
git push origin main
```

## Trabalhando com Seu Fork

Agora você pode trabalhar em seu fork normalmente:

```bash
# Crie uma nova branch para suas mudanças
git checkout -b minha-feature

# Faça suas alterações e commits
git add .
git commit -m "Descrição das mudanças"

# Envie para seu fork no GitHub
git push origin minha-feature
```

## Instalação e Configuração

Após clonar o repositório, siga as instruções de instalação:

1. Consulte o arquivo `doc/INSTALL` para instruções detalhadas de instalação
2. Configure o banco de dados conforme descrito na documentação
3. Instale as dependências com `bundle install`
4. Execute as migrações do banco de dados

## Recursos Adicionais

- Documentação oficial do Redmine: https://www.redmine.org/
- Guia de instalação: `doc/INSTALL`
- Guia de contribuição: `CONTRIBUTING.md`

## Observação Importante

Este é um fork do projeto Redmine oficial. Se você deseja contribuir com o projeto principal do Redmine, visite https://www.redmine.org/ e siga as diretrizes de contribuição oficiais.
