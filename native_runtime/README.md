# Runtime Linux nativo e portátil — ReqSys Redmine

## Objetivo

Retirar o Render do caminho crítico de desenvolvimento e homologação técnica sem
substituí-lo por outra dependência proprietária. O runtime é um contrato Linux
nativo que pode ser instalado em um host autorizado (PC24x7, Noteri, VM OCI ou
outro Linux compatível) sem Docker.

Este diretório **não provisiona uma VM**, não altera DNS, não publica ambiente e
não contém segredos.

## Layout

O instalador mantém releases imutáveis e estado separado:

```text
/opt/reqsys-redmine/
  current -> releases/<redmine-repo-sha>
  releases/<redmine-repo-sha>/
  shared/
    db/
    files/
    config/
    tmp/
    log/
    backups/
```

`current` só é trocado depois que a cópia, as dependências congeladas e a
identidade do release são verificadas. Repetir a instalação do mesmo SHA é
idempotente e não cria outro release.

O serviço systemd de referência usa `/opt/reqsys-redmine/current` e lê variáveis
de `/etc/reqsys-redmine/redmine.env`. Credenciais não pertencem ao repositório.

## Identidade do release

A instalação aceita apenas o build que contém
`public/reqsys-e2e/release-manifest.json` com o SHA esperado. Todos os artefatos
declarados nesse manifesto são relidos e re-hashados antes da mutação do
destino. O release nativo recebe um segundo recibo
`.reqsys-native-release.json`, que vincula:

- repositório;
- SHA do Redmine;
- hash do manifesto do build aprovado;
- hash da árvore da aplicação instalada;
- contrato dos diretórios persistentes.

O recibo é recalculável, mas não é assinatura criptográfica nem substitui um
atestado externo.

## Dependências

A instalação real usa o `Gemfile.lock` aprovado e executa Bundler em modo
`deployment/frozen`, com gems de runtime dentro de `vendor/bundle`. O modo
`--skip-bundle` existe apenas para os testes unitários e é recusado fora de
`REQSYS_NATIVE_TEST_MODE=1`.

O serviço lê `DATABASE_URL`. Para um ambiente permanente multiusuário,
PostgreSQL continua sendo o destino recomendado. Este primeiro incremento de
backup/restore suporta PostgreSQL 16 ou superior e exige `psql`, `pg_dump` e
`pg_restore` do mesmo major do servidor. A prova de backup descrita abaixo não
substitui o gate separado que deve comprovar que o release Rails instalado
contém o driver `pg`, migra e inicia contra o PostgreSQL do host permanente.

## Assets pré-compilados e release imutável

O Redmine 6.1 recompila assets automaticamente na inicialização quando detecta
mudanças. Isso altera `public/assets/.manifest.json` e é incompatível com o
contrato de release imutável e com `ProtectSystem=strict` do serviço nativo.

O instalador exige o contrato upstream esperado em
`config/environments/production.rb` e troca exatamente
`config.assets.redmine_detect_update = true` por `false` na cópia do release.
Os assets já foram pré-compilados e exercitados pelo build real anterior à
instalação nativa. `public/assets` continua dentro do hash da árvore da aplicação;
nenhum arquivo de assets é simplesmente ignorado para fazer o replay passar.
Se o upstream mudar esse contrato, a instalação falha fechada até nova revisão.

Referências oficiais:

- https://www.redmine.org/projects/redmine/wiki/RedmineInstall
- https://github.com/rails/propshaft

## Persistência e backup

`files`, `tmp`, `log` e o secret token gerado pelo Redmine são separados do
release. No teste de portabilidade, o SQLite do E2E é copiado de forma
consistente pela API de backup do SQLite para `shared/db/redmine.sqlite3`.

O backup SQLite:

- exige `--quiesced`;
- usa a API de backup do SQLite;
- inclui anexos e configuração persistente;
- escreve hashes SHA-256;
- recusa saída pré-existente;
- é verificado antes de ser aceito;
- contém material sensível de configuração e **não deve ser publicado em
  artifacts públicos ou Git**.

A restauração só aceita um destino novo, verifica todos os hashes e roda
`PRAGMA integrity_check` antes de concluir.

### PostgreSQL

O backup PostgreSQL usa `pg_dump --format=custom --no-tablespaces` e inclui, no
mesmo diretório privado, o dump, `shared/files` e `shared/config`. Os dois
componentes do filesystem são obrigatórios; ausência, link ou nó especial falha
fechado em vez de gerar um backup parcial. A aplicação e quaisquer workers
precisam estar efetivamente parados: `--quiesced` é uma declaração do operador,
não um mecanismo que interrompe processos. O snapshot transacional do
PostgreSQL não cria uma transação distribuída com os anexos do filesystem.

O manifesto schema 2 vincula o backup ao SHA e aos hashes do release nativo,
registra versões do servidor/cliente, encoding, `LC_COLLATE`, `LC_CTYPE`,
provider de locale, locale/regras ICU e versão de collation, além do perfil do
role do banco, identidade opaca do banco sem senha, readback lógico das tabelas
centrais do Redmine em `public` e SHA-256 de cada arquivo. A verificação
recalcula os hashes e exige que `pg_restore --list` leia o archive. Credenciais
são lidas de variáveis de ambiente e não são colocadas em argv, manifesto,
recibo ou saída normal. Os clientes usam modo sem prompt e não consultam
`~/.pgpass`.

A cópia aceita somente diretórios e arquivos regulares, usa abertura sem seguir
links e recusa FIFO, socket, device ou troca concorrente de inode. O destino do
backup não pode ficar sob `shared/files` ou `shared/config`, e o estado
restaurado não pode ficar dentro do próprio backup.

```bash
# Com o serviço/worker já parados e DATABASE_URL definido:
python3 native_runtime/native_runtime.py backup-postgresql \
  --target-root /opt/reqsys-redmine \
  --output /opt/reqsys-redmine/shared/backups/backup-2026-10-22 \
  --expected-sha "$RELEASE_SHA" \
  --quiesced

python3 native_runtime/native_runtime.py verify-backup \
  --backup-root /opt/reqsys-redmine/shared/backups/backup-2026-10-22 \
  --expected-sha "$RELEASE_SHA"

# REQSYS_RESTORE_DATABASE_URL deve apontar para outro banco criado de template0:
python3 native_runtime/native_runtime.py restore-postgresql \
  --backup-root /opt/reqsys-redmine/shared/backups/backup-2026-10-22 \
  --target-state /opt/reqsys-redmine-restored/shared \
  --expected-sha "$RELEASE_SHA"
```

O restore recusa o banco de origem e qualquer divergência de major, encoding ou
fingerprint completo de locale/collation. Tanto a origem quanto o destino devem
usar um role login que seja dono do banco, não tenha `SUPERUSER`, `CREATEDB`,
`CREATEROLE`, `REPLICATION` ou `BYPASSRLS` e não herde memberships efetivas
além do `pg_database_owner` implícito.

O destino deve ser criado de um `template0` confiável e permanecer quiescente.
O preflight faz um `pg_dump --schema-only` com ACLs e default ACLs preservadas e
exige TOC vazio; também bloqueia large objects, subscriptions, settings de
banco/role, prepared transactions, replication slots, ACL/owner inesperado do
banco e outras sessões cliente. Ele é repetido, com a verificação de sessões por
último, imediatamente antes do `pg_restore`. Ainda cabe ao operador impedir uma
nova conexão depois desse último check.

O restore também recusa `target-state` preexistente. Ele não usa `--clean`,
`--create`, roles, ownership, ACLs ou tablespaces da origem. Antes de alterar o
banco, compara novamente o hash do manifesto e todos os hashes da cópia em
staging. Após `pg_restore --single-transaction`, compara o readback `public.*` e
os anexos/config, remove a cópia temporária do dump e só então publica o estado
local com um recibo. Banco e filesystem não têm commit atômico comum: se houver
falha depois do commit do banco, o destino deve ser descartado e recriado antes
de nova tentativa.

SHA-256 detecta corrupção ou alteração sem recomputação do manifesto; não é uma
assinatura contra alguém capaz de substituir dados e manifesto. O hash do
manifesto precisa ser preservado em evidência externa. Backups contêm banco e
configuração sensível, usam permissões privadas e não podem ser publicados como
artifact ou enviados ao Git.

## systemd

`systemd/reqsys-redmine.service` é uma referência de serviço nativo. Ele não usa
Docker ou Render e aplica hardening básico (`NoNewPrivileges`, `PrivateTmp`,
`ProtectSystem=strict`, `ProtectHome=true`). O único caminho de escrita
permitido no layout de aplicação é `shared/`.

A instalação da unit em `/etc/systemd/system` e a criação do usuário `redmine`
são operações do host e devem passar pelo canal operacional autorizado do host.
Este incremento apenas versiona e valida o contrato.

## CI/E2E

`.github/workflows/native-linux-portability.yml` executa em Ubuntu hospedado
pelo GitHub:

1. testes unitários e controles negativos do instalador;
2. o build Redmine/ReqSys real já usado no DEV;
3. instalação nativa com dependências congeladas em `vendor/bundle`;
4. leitura Rails do banco persistente;
5. dois ciclos reais de Puma em loopback;
6. leitura SQLite independente após cada restart;
7. backup quiescido;
8. alteração controlada do backup, que deve ser detectada;
9. restauração em diretório isolado;
10. replay da instalação sem duplicar release;
11. SHA incorreto recusado antes de criar o destino;
12. backup PostgreSQL custom de banco, anexos e configuração;
13. adulteração do dump e SHA incorreto recusados antes do restore;
14. restore em dois bancos vazios, readback independente de contagens e valores,
    inclusive com `search_path` adversarial;
15. banco não vazio e replay no mesmo destino recusados sem alterar o primeiro
    restore.

O PostgreSQL do CI é uma fixture efêmera; nenhum backup é publicado como
artifact. Esse E2E comprova a portabilidade e o contrato de backup/restore no
runner Linux do GitHub. Não comprova systemd em host permanente, endpoint
público, PostgreSQL persistente, boot Rails usando PostgreSQL, segredos do host
nem a disponibilidade física do PC24x7.

## OCI Always Free

OCI é apenas um **destino candidato** para o mesmo contrato, não uma dependência
do código. Em 19/10/2026 a documentação oficial continua listando recursos
Always Free, incluindo Ampere A1 Arm e instâncias AMD, e alerta que:

- a capacidade Always Free pode estar temporariamente indisponível na região;
- instâncias ociosas Always Free podem ser recuperadas;
- A1 é Arm, portanto a arquitetura precisa passar pelo mesmo CI/E2E antes de
  promoção.

Referências oficiais:

- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://www.oracle.com/br/cloud/free/

Nenhuma tenancy ou VM OCI é criada por este incremento.
