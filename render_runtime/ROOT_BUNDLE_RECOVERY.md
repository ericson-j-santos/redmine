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

Gemfile.lock gerado: SHA-256
`595a2c459c9ff1e5f3650d7277267d0d9a3f8be63834dfbf38df71992bc21e28`,
blob Git `62521bc62544435cef3a2739afb414dc550781ee` (14.450 bytes).
Os bytes transportados foram conferidos por ambos os hashes antes do commit.

## Prova do candidato e prevenção permanente

O candidato passou instalação congelada, bundle check, auditoria bloqueante,
migrações reais e suites da raiz: Attachment 51 testes/162 asserções, Mailer
83 testes/627 asserções, sem falhas, erros ou skips. A auditoria não encontrou
vulnerabilidades na base fa2295251efb3b0d1a300e5ce8ad700ff1f1b485.
Esses números pertencem ao candidato: o CI do commit final deve revalidá-los.

O workflow passa a usar exclusivamente o modo verify: instala o lock versionado
sem resolver versões novas ou modificá-lo silenciosamente. O controle negativo
muda temporariamente o pin Rails somente no worktree descartável, exige a recusa
do Bundler congelado, restaura o arquivo em finally e repete bundle check. Falha
por rede ou outro motivo não conta como recusa válida. Sete testes de política
incluem esse contrato; aceitar qualquer resultado foi detectado por mutação.

Permanecem obrigatórios os jobs históricos lint/bundle-audit e o E2E isolado
ReqSys/Redmine. Nenhum gate foi removido. Sem cache do bundle histórico no novo
executor, sem segredos externos, sem escrita remota pelo CI e sem artifacts.

## Limites e reversão

Esta validação é da raiz em isolamento, não publicação, SMTP externo, miniaturas
PDF ou homologação das demais plataformas/bancos da matriz histórica. O log do
candidato registra Ghostscript ausente, dependência observer implicitamente
carregada pelo factory_bot e depreciação de omniauth-azure. Esses avisos não
foram ocultados e não autorizam migração de autenticação nesta alteração.

Rollback: reverter o commit da branch preserva os serviços e dados externos,
mas volta ao bundle vulnerável; isso não autoriza sua implantação. Render
permanece sem deploy automático e nenhuma implantação foi realizada.

Checkpoint canônico: ReqSys issue #1686 / TODO-7.
Correlation ID: redmine-root-lock-20261019-todo7.

## Compatibilidade Ruby após a atualização de segurança

O job histórico 117909828962, no SHA d33f7072, comprovou que css_parser 3.3.0
exige Ruby >= 3.3 e não instala no Ruby 3.2.11. A versão corrigida não é
rebaixada para contornar a auditoria. O Gemfile agora impõe Ruby >= 3.3 e < 3.5;
lint e bundle-audit usam 3.3. A matriz mantém todos os bancos e comandos de
teste em 3.3/3.4, retirando apenas o intérprete 3.2 que deixou de ser suportado.
Isso não constitui homologação automática da matriz nem altera Ruby no Render.

Uma oitava regressão verifica o mínimo declarado e os dois jobs históricos;
os controles com mínimo antigo ou CI em 3.2 falham. O lock permanece exatamente
como gerado pelo Bundler, inclusive seu campo histórico RUBY VERSION; esse
campo não substitui a observação do intérprete e a instalação congelada real.
A mudança de requisito e todos os gates exigem nova prova no SHA final.
