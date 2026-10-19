# Proveniência da publicação DEV

## Contrato implementado

O build captura a identidade antes de reservar `.runtime`, baixar dependências
ou escrever no banco isolado. A captura exige o SHA completo e compara todos os
arquivos rastreados de `render_runtime` com os blobs Git daquele commit.
Arquivos ausentes, alterados, extras ou substituídos por links simbólicos causam
recusa. O build desativa geração de bytecode Python para manter essa fonte
inalterada, e a captura é repetida antes da gravação do manifesto.

Em Render, a origem é vinculada às variáveis nativas `RENDER`,
`RENDER_SERVICE_ID`, `RENDER_GIT_REPO_SLUG`, `RENDER_GIT_BRANCH` e
`RENDER_GIT_COMMIT`, ao serviço DEV `srv-dathlk2d0e5s73c5722g`, ao repositório
e à branch DEV já existentes. Contexto parcial ou divergente falha fechado:
não há fallback silencioso para CI. A disponibilidade real do checkout Git
e desses metadados no build Render ainda exige execução nesse ambiente.

Em GitHub Actions, somente a rota `github-hosted` do repositório e da branch
esperados é aceita. O SHA é comparado ao checkout, e os bytes da cópia usada
pelo build são comparados diretamente com os blobs desse checkout. A string
do SHA, sozinha, não comprova a cópia.

## Evidência e manifesto

O JSON `public/reqsys-e2e/evidence.json` passa a incluir `redmine_repo_sha` e
`source_identity`. A serialização completa é novamente verificada contra a
chave real antes da gravação.

Depois do E2E e da validação de compatibilidade, o build cria
`public/reqsys-e2e/release-manifest.json` com:

- identidade da fonte e método de observação;
- versão Redmine observada, SHA ReqSys e identidade do harness;
- hashes SHA-256 de `Gemfile.lock`, `config/database.yml`,
  `lib/redmine/version.rb` e dos bytes finais de `evidence.json`;
- escopo explícito de build isolado.

A lista de arquivos é fixa e não inclui banco, anexos, configuração de segredo,
token ou logs. A gravação é exclusiva, sem substituir manifesto existente.
O build relê os bytes, recalcula os hashes e só então cria o alias legado
de inicialização. O startCommand do serviço não é alterado por este incremento.

O job real existente verifica a cópia antes do build: SHA divergente e fonte
alterada devem ser recusados, com restauração dos bytes e replay sem reserva.
Depois lê o manifesto com o `GITHUB_SHA` observado pelo executor.
Executa quatro controles negativos em cópia separada: SHA esperado divergente,
SHA do manifesto alterado, lock alterado e evidência alterada. Cada controle
deve falhar; os bytes são restaurados e a verificação é repetida. O runtime real
e seu SQLite não são alterados por esses controles. A leitura SQLite independente
e as verificações ReqSys ↔ Redmine continuam obrigatórias.

## Limites de publicação e preservação

Este manifesto detecta incoerência entre a fonte observada, a evidência e os
arquivos selecionados. Não é assinatura de terceiros, backup, autorização de
deploy, prova de prontidão HTTP ou proteção contra adulteração coordenada por
um agente com escrita sobre código, manifesto e evidência.

`git HEAD == RENDER_GIT_COMMIT` não fixa o SHA escolhido para a publicação
contra avanço da branch. A operação de publicação deve selecionar externamente
o commit exato, por `commitId` na API oficial ou capacidade equivalente do painel,
e conferir o SHA do deploy retornado. A ação Render exposta nesta sessão não
aceita esse parâmetro; não usar um trigger da branch como substituto.

O runtime Redmine baixado continua gerando seu próprio lock e o auditando em
cada build. O hash registrado identifica o lock observado: não transforma essa
instalação no artefato binário do CI, nem estende a ela o contrato frozen da raiz.
A raiz e seu lock não são alterados por este incremento.

O serviço Free tem filesystem efêmero. O build não alcança nem copia o SQLite
ou os anexos do deploy anterior. A autorização condicional já registrada pelo
proprietário — descarte somente se não houver alternativa — permanece restrita
a esse DEV. Verificar primeiro a possibilidade de exportação lógica autenticada.
Preservação exige cópia consistente de banco e anexos e restauração comprovada.
Rollback de código não restaura esses dados.

## Referências verificadas em 19/10/2026

- Variáveis nativas: https://render.com/docs/environment-variables
- Deploy por commit: https://api-docs.render.com/reference/create-deploy
- Filesystem e recursos do Free: https://render.com/docs/free
- Autorização condicional e limites:
  https://github.com/ericson-j-santos/reqsys-v2-enterprise-real/issues/1686#issuecomment-6278669363
- Continuidade do CI:
  https://github.com/ericson-j-santos/reqsys-v2-enterprise-real/issues/1686#issuecomment-6275351762

Validação deste incremento deve ser registrada no checkpoint com o SHA final,
os runs/jobs efetivamente executados, hashes e limites. Nenhum resultado anterior
comprova automaticamente este novo contrato.
