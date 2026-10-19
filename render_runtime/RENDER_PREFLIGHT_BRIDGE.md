# Ponte de preflight Render DEV — TODO-7

Este incremento qualifica uma rota GitHub Actions -> API oficial Render sem
usar Browser, RDC, shell do serviço, nova credencial ou infraestrutura paga.
Não é um executor de deploy: seu cliente HTTP só aceita GET para o serviço DEV
srv-dathlk2d0e5s73c5722g e suas variáveis diretas.

O workflow render-dev-preflight.yml dispara somente no push da branch DEV
existente quando seus arquivos mudam, sem agenda, PRs ou publicação automática.
Tem concorrência exclusiva, timeout de três minutos, contents:read e checkout
no SHA exato sem persistir credenciais. Os testes rodam sem secrets; somente a
etapa de qualificação recebe a referência secrets.RENDER_API_KEY. Isso não cria
o secret, não o copia de outro workload e não prova que esteja provisionado.

A falta da referência utilizável termina com exit 2 e
RENDER_CREDENTIAL_NOT_AVAILABLE, antes de qualquer rede. Não é conclusão verde.
HTTP 401/403, redirect, erro, resposta excessiva, configuração incompatível ou
mudança de metadados entre duas leituras falham sem retry, sem corpo HTTP e sem
valores sensíveis nos logs. Não há busca de token em arquivos ou login local.

Com acesso, o script confere workspace, serviço, repositório, branch, plano
Free, Ruby e comandos existentes. Lê variáveis apenas em memória e devolve
booleanos. O endpoint não retorna grupos de ambiente: variáveis não confirmadas
diretamente ficam não comprovadas, não são declaradas ausentes globalmente.

A saída contém um plano não executado com commitId completo e clearCache
do_not_clear, separado da verificação do transporte GET. Mesmo no caso positivo,
deployment_ready, post_transport_verified e data_preservation_verified ficam
false. Não há POST, PATCH, DELETE, gravação de configuração ou exportação de
dados nesta CLI. CI em curso e GET 200 não autorizam publicar.

A decisão do proprietário em 19/10/2026 continua condicional: descarte somente
se não houver alternativa viável, exclusivamente no DEV identificado. A
preservação/exportação e sua verificação permanecem anteriores a qualquer
aplicação dessa decisão. O Redmine histórico permanece fora do escopo.

Validação: 18 testes locais de identidade, plano com SHA, contexto, segredo
ausente, redirecionamento, limite, erros sanitizados, replay e leitura
independente. Controle por mutação deve detectar deployment_ready indevido.
Fixtures e transportes simulados não comprovam autenticação Render real;
o resultado da etapa real deve ser lido no run do SHA publicado.

Próximo gate: com referência autenticada comprovada, verificar preservação,
CI do SHA, plano/reversão e condições da autorização; somente então implementar
e validar POST controlado, identidade do deploy retornado e E2E publicado.
Não rerodar sem mudança de código ou de pré-condição.

Fontes primárias:
- https://api-docs.render.com/reference/create-deploy
- https://api-docs.render.com/reference/retrieve-service
- https://api-docs.render.com/reference/get-env-vars-for-service

Continuidade: ReqSys issue #1686 / TODO-7.
Correlation ID: redmine-render-readonly-bridge-20261019-todo7.
