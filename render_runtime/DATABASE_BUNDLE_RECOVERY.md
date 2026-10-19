# Contrato do bundle dos bancos — candidato

Correlação: redmine-ci-contracts-20261019-todo7.

## Evidência de origem

No SHA d9ba2059cb0bf9cfc2c563a715133a0df55ce206, os quatro jobs de
PostgreSQL/MySQL do run 39315539687 recusaram o Gemfile antes de migrar:
o setup escolhe somente um banco, removendo sqlite3 do conjunto avaliado e,
no MySQL, acrescentando mysql2 e with_advisory_lock. Os serviços estavam
saudáveis. O lock é o blob 41ac12fcfa7632e300e036e59d77d75c1c421f2b.

## Geração explícita

O modo database-candidate altera somente uma worktree descartável no runner
GitHub hospedado. Mantém o verify congelado já existente. O Bundler 2.6.7
gera o candidato com bundle lock, sem --update. O contrato aceita apenas
mysql2 0.5.7 e with_advisory_lock 7.6.0: bigdecimal e activerecord, suas
dependências de runtime, já estão no lock.

O validador retira somente esses dois blocos novos e suas dependências
diretas do candidato em memória. Todos os bytes residuais devem ser iguais
ao lock de origem. As constantes de revisão nunca são usadas para escrever
um lock. Gemfile e lock completos só são emitidos após instalação congelada,
controles negativos, auditoria, migração e suites reais no SQLite.

## Verificação de contrato

O probe usa o DSL real do Bundler 2.6.7 para avaliar cópias do Gemfile e do
Gemfile.local em SQLite, PostgreSQL, MySQL e configuração ausente. Compara
nomes, requisitos e plataformas com o lock, verifica grupos e require:false,
rejeita uma dependência extra e um carregamento alterado, repete o positivo
e comprova preservação dos arquivos de origem.

A compilação/instalação das gems, as migrações e suites reais de todos os
bancos continuam obrigatórias. O probe DSL não comprova conexão a banco.
A árvore corrente não contém Gemfiles de plugins; sua introdução exige
revisão explícita da cópia do probe. O formato permitido do lock é o atual,
com uma origem RubyGems e sem seções novas.

## Estado

Preparação em revisão; ainda não é resultado aprovado. Nenhum deploy, merge,
banco persistente, credencial ou privilégio foi alterado.
