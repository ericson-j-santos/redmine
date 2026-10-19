# Recuperação do bundle da raiz — TODO-7

## Causa e alteração

A raiz é a aplicação histórica com Rails 8.0.3; seu Gemfile.lock não é o bundle
Rails 7.2.4 do release Redmine 6.1.5 baixado por render_runtime. Corrigir somente
esse release não eliminava os alertas do job bundle-audit da raiz.

O candidato foi resolvido pelo Bundler 2.6.7 real em Ruby 3.3.12, no run
39205046715/job 117905943569, a partir do SHA 4c0d2afdcbd93bb4c45718915a3f7370509f46f2.
O Gemfile muda cinco declarações: Rails 8.0.5.1, mail 2.9.1, Nokogiri ~>1.19.4,
rubyzip 3.4.1 e sqlite3 ~>2.9.6. Dependências transitivas foram resolvidas pelo
Bundler; o lock não foi copiado do runtime nem reconstituído por troca de versões.

O primeiro lock nativo tinha SHA-256
`595a2c459c9ff1e5f3650d7277267d0d9a3f8be63834dfbf38df71992bc21e28`
e blob `62521bc62544435cef3a2739afb414dc550781ee` (14.450 bytes).
O metadado Ruby desse candidato foi corrigido posteriormente como descrito abaixo.

## Compatibilidade Ruby e lock final

O job histórico 117909828962, no SHA d33f7072, comprovou que css_parser 3.3.0
exige Ruby >= 3.3 e não instala no Ruby 3.2.11. A versão corrigida não foi
rebaixada para contornar a auditoria. O Gemfile agora impõe Ruby >= 3.3 e < 3.5;
lint e bundle-audit usam 3.3. A matriz mantém bancos e comandos de teste em
3.3/3.4, retirando o intérprete 3.2 que deixou de atender aos requisitos.
Isso não constitui homologação automática da matriz nem altera Ruby no Render.

O gate congelado do run 39207791537/job 117914304990 recusou o campo histórico
RUBY VERSION 3.2.3p157. Esse resultado corrigiu a hipótese anterior de que
bastaria mudar o requisito do Gemfile mantendo o metadado antigo do lock.

No run 39208376589/job 117916073550, SHA b050426150978f3ae2abd7bcccabb7a70789ffdf,
`bundle update --ruby` gerou nativamente `ruby 3.3.12p206`. O executor comprovou
igualdade de todos os bytes fora do bloco RUBY VERSION; nenhuma gem mudou.

Lock final nativo, agora versionado (14.451 bytes):
- SHA-256: `1dc8af4dc60dbdee074615e3e49e2a6901ecea30f16c5c80f2d36d2e400bacd4`.
- Blob Git: `74f0bf582977eafef79753a0ae63f11413cfd37c`.

## Prova do candidato e prevenção permanente

O candidato com o metadado corrigido passou instalação congelada, bundle check,
controle negativo real, restauração/replay, auditoria bloqueante, migrações e
suites da raiz: Attachment 51 testes/162 asserções e Mailer 83/627, sem falhas,
erros ou skips. A auditoria não encontrou vulnerabilidades na base
fa2295251efb3b0d1a300e5ce8ad700ff1f1b485. Esses resultados pertencem ao candidato
b050426; o CI do commit final deve confirmar o lock efetivamente versionado.

O workflow normal volta exclusivamente ao modo verify: instala o lock versionado
sem resolver versões novas nem regenerar metadados silenciosamente. Modos de
preparação são explícitos e nunca transformam um candidato em prova de commit.
O controle negativo altera temporariamente o pin Rails somente no worktree
descartável, exige a recusa específica do Bundler congelado, restaura o arquivo
em finally e repete bundle check. Erro de rede não conta como recusa válida.

Onze testes de política cobrem fonte, resumos, recusa congelada, mínimo Ruby,
jobs históricos e metadado do lock versionado. O controle com o lock antigo
3.2 falhou; restaurado o lock final, os onze testes passaram. Mutação que
permitia alteração de dependências durante a correção do metadado também falhou.

Permanecem os jobs históricos lint/bundle-audit e o E2E isolado ReqSys/Redmine.
Nenhum alerta foi ignorado. O novo executor não usa cache histórico, credenciais
externas, escrita remota, artifacts ou agendamento recorrente.

## Limites e reversão

Esta validação é da raiz em isolamento, não publicação, SMTP externo, miniaturas
PDF ou homologação das demais plataformas/bancos da matriz histórica. O log
registra Ghostscript ausente, observer implicitamente carregado por factory_bot
e depreciação de omniauth-azure. Esses avisos não foram ocultados e não autorizam
migração de autenticação nesta alteração.

Rollback: reverter o incremento na branch preserva os serviços e dados externos,
mas volta ao bundle vulnerável; isso não autoriza sua implantação. Render
permanece sem deploy automático; nenhuma implantação foi realizada.

Checkpoint canônico: ReqSys issue #1686 / TODO-7.
Correlation ID: redmine-root-lock-20261019-todo7.
