# ReqSys Redmine DEV runtime

Runtime isolado usado somente para o E2E da issue ReqSys #1686.

- baixa o release oficial Redmine 6.1.4;
- valida SHA-256 oficial antes de executar;
- usa Postgres separado;
- habilita REST API;
- cria/reconcilia projeto e usuário de serviço de forma idempotente;
- a API key entra somente por variável de ambiente e nunca é impressa.

O serviço Render aponta para esta branch, não para o Redmine histórico.
