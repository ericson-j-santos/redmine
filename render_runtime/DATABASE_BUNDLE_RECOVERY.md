# Contrato congelado dos bancos

Correlação: redmine-ci-contracts-20261019-todo7.

## Origem reconciliada

No SHA d9ba2059cb0bf9cfc2c563a715133a0df55ce206, os quatro jobs de
PostgreSQL/MySQL do run 39315539687 recusaram o Gemfile antes de migrar:
o setup escolhe somente um banco, removendo sqlite3 do conjunto avaliado e,
no MySQL, acrescentando mysql2 e with_advisory_lock. Os serviços estavam
saudáveis. A falha não era de conexão nem de QueryTest.

## Lock gerado e relido

O Bundler 2.6.7 gerou o candidato nativamente com bundle lock, sem --update,
na worktree descartável do SHA aac3e20d1c7466504af2a64628a359654d16c4d0.
Evidência: https://github.com/ericson-j-santos/redmine/actions/runs/39321428224
(job 118296180575).

- Origem: blob 41ac12fcfa7632e300e036e59d77d75c1c421f2b, 14493 bytes.
- Resultado: blob fda9cb9c8dc00b51912830d6d4f1886eed1e10dc, 14629 bytes.
- SHA-256: 60716da8058c1ead17cd8cb003ef1448ab29db8a1a7fae8b4356298dd581e8a3.
- Somente mysql2 0.5.7 e with_advisory_lock 7.6.0 foram acrescentados.
- bigdecimal 4.1.3 e activerecord 8.0.5.1, suas transitivas, já existiam.
- Após retirar os dois blocos novos e as duas linhas diretas do candidato
  em memória, todos os bytes residuais são idênticos ao lock original.

Os bytes completos foram emitidos somente depois de instalação congelada,
FactoryBot/observer real, controles negativos Rails/observer/mysql2 com
restauração, auditoria, migração e 169 testes/864 asserções sem falhas, erros
ou skips em Ruby 3.3.12. Esses resultados validam o candidato de geração;
a matriz do commit que incorpora estes bytes precisa ser conferida à parte.

## Contrato permanente

Os complementos dos bancos inativos ficam somente em :test, require:false.
O case seleciona flags; cada gem tem uma única declaração fora dos grupos.
Adaptadores ativos recebem opções vazias (grupo padrão e carregamento
original); os demais recebem group:test e require:false. Assim o lint de
duplicação permanece habilitado e o probe continua exigindo esses grupos.
O probe usa o DSL real do Bundler 2.6.7 sobre o Gemfile e Gemfile.local em
SQLite, PostgreSQL, MySQL e configuração ausente. Compara nomes, requisitos
e plataformas com o lock, verifica grupos e carregamento, rejeita uma
dependência extra e require:true, repete e verifica os arquivos de origem.

O modo verify nunca resolve: exige o contrato, instalação congelada,
controle negativo real removendo mysql2, restauração e novo probe, além dos
controles de observer/Rails e auditoria já existentes. O passo temporário
database-candidate foi retirado do workflow.

A matriz exige conexão real, identidade do banco consultada no servidor ou
arquivo SQLite e repetição de SELECT 1, sem alteração do lock, antes da
regressão Git e suíte ampla. As execuções focadas Git e Bazaar recebem uma
chave de teste efêmera somente no subprocesso; sua saída é redigida se
contiver a chave. O locale ISO do teste Bazaar foi preservado.

## Limites e continuidade

A árvore atual não contém Gemfiles de plugins; sua introdução exige revisão
da cópia usada pelo probe. O formato permitido do lock é o atual, com uma
origem RubyGems e sem seções novas. As constantes de revisão nunca geram
lockfiles.

Esta recuperação não é deploy nem homologação do DEV publicado/PC24x7.
O E2E do build isolado usa o runtime próprio de render_runtime; não equivale
à validação funcional desses ambientes ou da projeção do TODO Global.
O TODO-7 permanece aberto e E2E parcial até suas evidências reais.

O Gemfile foi consolidado após o lint detectar declarações duplicadas nos
ramos condicionais. O lock nativo acima permanece byte-idêntico. A chave
require é omitida para adaptadores ativos: require:nil não seria equivalente
no DSL do Bundler 2.6.7. O probe mantém essa distinção obrigatória.
