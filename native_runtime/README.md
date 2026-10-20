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

O serviço usa `DATABASE_URL`, permitindo trocar SQLite por PostgreSQL sem
reescrever o release. Para um ambiente permanente multiusuário, PostgreSQL
continua sendo o destino recomendado; o primeiro incremento de backup/restore
implementado aqui cobre SQLite e mantém PostgreSQL como gate explícito antes de
promoção permanente.

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
11. SHA incorreto recusado antes de criar o destino.

Esse E2E comprova a portabilidade no runner Linux do GitHub. Não comprova
systemd em um host permanente, endpoint público, PostgreSQL persistente, backup
PostgreSQL nem a disponibilidade física do PC24x7.

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
