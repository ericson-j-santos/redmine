# Dependência de testes observer — TODO-7

## Causa e correção mínima

O job histórico SQLite/Ruby 3.4 `117920432767` falhou antes dos testes:
`factory_bot 6.2.1` carregava `observer`, ausente do bundle explícito.
A correção declara `observer 0.1.2` somente no grupo `test`, com `require: false`.
Não atualiza factory_bot nem qualquer versão já presente no lock auditado.

## Origem verificável do lock

O Bundler 2.6.7 executado em Ruby 3.4.11 gerou o candidato no run
`39286162191`, job `118172776626`, SHA
`453aac17939d0b2ebbdd2e4d3aa60543f3ac5d7d`.
A comparação bloqueante aceitou somente duas linhas novas de observer.
Todos os outros bytes, inclusive plataformas e metadado Ruby, foram preservados.

- Lock: 14.493 bytes.
- Git blob: `41ac12fcfa7632e300e036e59d77d75c1c421f2b`.
- SHA-256: `0c3e5316f7b2403d381b87b79a52f591dfb536315c6f27dc524964ffeb753c71`.

O candidato passou boot real do FactoryBot, instalação congelada, controles
negativos de Rails e observer, restauração/replay, auditoria, migrações e
134 testes Ruby / 789 asserções, sem falhas, erros ou skips.
Isso é prova do candidato isolado; cada commit final exige nova execução.

## Prevenção e limites

O workflow normal volta a `verify`, sem regeneração silenciosa do lock.
Valida Ruby 3.3 e 3.4 sequencialmente, em worktrees descartáveis, sem segredos
externos nem permissões de escrita. O contrato sobre os arquivos versionados
rejeita a remoção de observer e a volta acidental ao modo candidato.
Os oito testes de política específicos não substituem boot, auditoria ou E2E.

O PostgreSQL/Ruby 3.3 teve outra causa comprovada no job `117920433046`:
a seleção do adaptador remove sqlite3 do Gemfile avaliado e o Bundler congelado
rejeita a divergência com exit 16. Essa matriz não foi corrigida por observer.
Permanecem obrigatórias a análise da suíte ampla SQLite e das demais falhas,
a preservação de dados e a homologação do DEV publicado/PC24x7/TODO Global.
Ghostscript/PDF, SMTP externo e autenticação Microsoft real não estão cobertos
pelos testes direcionados. Nenhum deploy é autorizado por este documento.

Reversão: reverter conjuntamente este incremento de Gemfile/lock/contrato;
reverter somente a declaração deve falhar no CI, não desbloquear a publicação.
Em caso de estado resumido divergente, conferir etapas e logs do mesmo run/SHA
pela leitura direta antes de declarar fila, bloqueio, conclusão ou repetir jobs.

Checkpoint: ReqSys issue #1686 / TODO-7.
Correlation ID: `redmine-observer-20261019-todo7`.
