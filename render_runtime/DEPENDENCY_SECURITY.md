# Dependências do runtime Redmine isolado — TODO-7

## Escopo e causa

O Redmine 6.1.5 baixado pelo build restringia mail a 2.8.x, rubyzip a 2.4.x e
sqlite3 a 2.5.x. A auditoria do lock realmente instalado reprovou essas famílias
no run 39175431412/job 117817017464; repetir bundle install não as corrigiria.

A política versionada preserva Rails, a versão Redmine, o checksum do arquivo
oficial e o produto/harness ReqSys já fixados. Ela atualiza mail 2.9.1,
rubyzip 3.4.1 e sqlite3 2.9.6 e move Puma do grupo exclusivo de testes para o
bundle de runtime, fixado em 7.2.1. A promoção de Puma corrige a dependência
implícita do executável global do runner que impedia a instalação portátil
congelada. Os pins não são atestado de ausência de vulnerabilidades.

## Proteções

- O Gemfile original deve corresponder exatamente ao blob upstream
  `0db3edefdabf92e376c05a10c6bdaf48663fe16f`. A fixture conserva esses bytes.
- Patch parcial, upstream modificado, alvo não regular, hardlink, disputa de lock
  ou alteração concorrente falham fechados. A substituição é atômica e o replay
  completo não regrava o Gemfile.
- A CLI aceita somente o runtime descartável reservado pelo build. Não recebe
  caminho arbitrário, não acessa o serviço publicado e não configura segredos.
- A auditoria agora também ocorre dentro do build, antes da compatibilidade e
  da liberação do alias de inicialização. A auditoria independente do CI continua.
- As suites upstream `attachment_test.rb` e `mailer_test.rb` executam em banco
  SQLite exclusivo de teste, distinto do banco do lifecycle. E-mail fica no
  adaptador de teste do Rails, não constitui teste de entrega SMTP.
- Python confere que cada suite tem ao menos cinco testes não pulados, asserções,
  zero falhas/erros, as quatro versões efetivamente carregadas (incluindo Puma)
  e o lock utilizado.
- O lifecycle real ReqSys/Redmine e a releitura SQLite independente permanecem
  obrigatórios. Não apresentar testes de transporte simulado como E2E externo.

## Validação e limites

Os testes locais da política incluem caso anterior reprovado, entradas negativas,
replay sem escrita, lock concorrente, rollback da escrita interrompida, links,
versão carregada incorreta, lock de outra plataforma e resumo de testes ausente
ou todo pulado. O job existente descobre esses testes sem novo workflow.

A homologação final depende do CI do novo SHA, incluindo sintaxe Bash, instalação
limpa, suites Ruby, lifecycle real e auditoria do lock. O checkpoint operacional
da issue #1686 registra o resultado observado, não este documento prospectivo.

Os jobs históricos de lint/bundle-audit do repositório não são removidos nem
considerados corrigidos por esta mudança no runtime baixado. Dados persistentes,
backup/restauração, autorização de deploy, E2E publicado, PC24x7 e projeção do TODO
Global continuam fora desta validação isolada.

Rollback: reverter o incremento no branch DEV restaura o código anterior, mas
não autoriza implantar seu bundle vulnerável. Nenhum banco externo é alterado.

## Fontes primárias

- https://github.com/redmine/redmine/blob/6.1.5/Gemfile
- https://github.com/mikel/mail/security/advisories/GHSA-mvxr-6m87-mv2q
- https://rubygems.org/gems/rubyzip/versions/3.4.1
- https://github.com/sparklemotion/sqlite3-ruby/security/advisories/GHSA-mwm8-39rw-8826

Continuidade: https://github.com/ericson-j-santos/reqsys-v2-enterprise-real/issues/1686
Correlation ID: `redmine-dependencies-20261018-todo7`
