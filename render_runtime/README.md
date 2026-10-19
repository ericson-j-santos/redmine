# ReqSys Redmine DEV runtime

Runtime isolado da issue ReqSys #1686. Não é a instância Redmine histórica,
não é o TODO Global canônico e não está homologado para dados duráveis.

## Incrementos de recuperação — 18–19/10/2026

O entrypoint `build_redmine_6_1_4.sh` é mantido por compatibilidade com o serviço
Render existente; o código passa a baixar **Redmine 6.1.5**. O SHA-256 fixado vem
da página oficial de downloads e é verificado antes da extração:

`4b653d8863c012fdb226aedf6f8a18bdfa08d04625d15e8aafbbc3c4f6b70144`

O código do produto ReqSys é fixado em
`9be16bfee3a3b8f9e3478e197e77d9231cdc4be6`. Esse SHA não contém o script E2E
histórico. O build importa somente esse script do commit
`b84576f76fad584bc420cb447d046aaafdc775ba`, verificando o blob Git
`4008741f26abc4a1487978682ad53d17b9f20adc`; o restante da árvore e das importações
continua no SHA atual escolhido do produto. Ambas as identidades entram na
evidência. Isso não comprova, por si só, compatibilidade: o E2E precisa executar.

## Dados existentes: bloqueio antes de qualquer limpeza

Não há mais `rm -rf` no build. `runtime_safety.py reserve` usa `mkdir` exclusivo
para reservar `.runtime`; diretório, arquivo ou symlink existente causam
`REDMINE_RUNTIME_EXISTS_PRESERVED`, sem sobrescrever conteúdo.
Reservas concorrentes têm um único vencedor. Uma tentativa interrompida deixa
seu diretório e diagnóstico preservados; repetição falha de forma não destrutiva.

Uma instalação nova exige `REQSYS_REDMINE_EPHEMERAL_E2E=1`, referência válida de
`REQSYS_REDMINE_API_KEY` e identificador de projeto válido. A variável de escopo
não autoriza deploy nem dispensa comprovação de que o alvo é descartável.
O código não configura essa variável no serviço nem cria ou rotaciona segredos.

**Limite importante:** recusar a limpeza local não garante persistência entre
deploys no Render Free. O banco continua SQLite conforme `database.yml`.
Dados a preservar exigem backup/restauração e armazenamento durável comprovados
antes de implantar. Este incremento não copia nem migra o banco do serviço atual.

## Versão e caminho de inicialização

O código executa a versão extraída para observar `Redmine::VERSION.to_s` e
compará-la à versão esperada. O E2E recebe a versão observada, não uma declaração
fixa antiga. Somente após o E2E e a validação da evidência passarem, cria o alias
relativo `.runtime/redmine-6.1.4 -> redmine-6.1.5`, sem substituir destino existente.

Assim, o startCommand já configurado pode continuar apontando para o caminho
legado. O nome do entrypoint, da branch e do serviço não representa a versão
instalada. A versão efetivamente publicada ainda exige leitura pós-deploy.

## Projeto e isolamento

O bootstrap Ruby existente continua sendo uma etapa de escrita. Após iniciar
o Puma local, o build consulta a API por `REQSYS_REDMINE_PROJECT_IDENTIFIER`
(padrão `reqsys-e2e-dev`) e exige identidade exata, projeto privado e ID inteiro
positivo. Não presume ID 1. A consulta aceita somente loopback, sem proxies ou
redirecionamentos, com timeout e limite de resposta; erros não expõem conteúdo
nem chave. O banco ReqSys e o log do Puma ficam na reserva exclusiva do build,
não em caminhos globais fixos em `/tmp`.

## Evidência e prevenção

`public/reqsys-e2e/evidence.json` exige resultado positivo, controles de replay e
quarentena, correlação, SHA/versão/projeto coerentes e ausência da chave real no
JSON. O arquivo não é sobrescrito e recebe releitura independente. Sua origem
é marcada como build isolado, não como prova pós-deploy ou integração PC24x7.

Os testes em `render_runtime/tests/test_runtime_safety.py` exercitam SQLite real
em diretório temporário, disputa de reserva, repetição, links, HTTP loopback,
redirecionamento, respostas inválidas e publicação de evidência. O servidor HTTP
de teste é um controle local, não uma instância Redmine. O job adicional no
workflow `Lint` existente valida sintaxe Bash/Ruby/Python e executa essa suíte
somente na branch DEV correspondente, sem secrets, cache novo ou artifacts.

## Identidade da fonte e manifesto

O contrato de proveniência e a conferência independente dos artefatos estão
em [RELEASE_IDENTITY.md](RELEASE_IDENTITY.md). O build identifica o SHA Redmine
na evidência pública e gera um manifesto verificável. Isso não substitui o
despacho do commit exato, a proteção dos dados ou a validação pós-publicação.

## Estado operacional e aceite pendente

O último estado observado do serviço `redmine-reqsys-e2e-dev-614` permanece Ruby
nativo, plano Free, deploy automático desativado e build anterior falho
`dep-dathve893c1s73am6ua0`. A causa específica desse exit 1 não foi comprovada;
este incremento corrige riscos reproduzidos no código, não inventa essa causa.

Ainda são obrigatórios: disponibilidade do arquivo oficial e validação do
checksum no build; compatibilidade Ruby/gems/Python; validação do alvo descartável
ou backup/restauração; autorização de implantação; E2E real no mesmo SHA;
prontidão, versão e leitura independente após publicação; integração PC24x7 e
projeção TODO Global. Não ativar recorrência nem declarar recuperação por CI verde.

Fontes oficiais consultadas em 18/10/2026:
- https://www.redmine.org/projects/redmine/wiki/Download
- https://www.redmine.org/projects/redmine/wiki/Security_Advisories

Continuidade: https://github.com/ericson-j-santos/reqsys-v2-enterprise-real/issues/1686
