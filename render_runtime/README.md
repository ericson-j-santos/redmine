# ReqSys Redmine DEV runtime

Runtime isolado usado somente para o E2E da issue ReqSys #1686.
Não é a instância Redmine histórica nem o runtime canônico do TODO Global.

## Estado observado em 18/10/2026

A configuração abaixo foi conferida no código da branch
`dev/reqsys-e2e-redmine-6.1.4-20260928`, em
`bb632f3c23e45e56df73cb89331b67851c1fdf91`, e nos metadados do serviço
Render `redmine-reqsys-e2e-dev-614`.

| Componente | Configuração observada |
| --- | --- |
| Runtime | Ruby nativo; sem Docker neste serviço |
| Release fixado no build | Redmine 6.1.4 |
| Banco Redmine | SQLite, conforme `database.yml` |
| Arquivo do banco | `.runtime/redmine-6.1.4/tmp/reqsys_redmine_e2e.sqlite3` |
| Dependência ReqSys do E2E | `b84576f76fad584bc420cb447d046aaafdc775ba` |
| Diretório de inicialização no Render | `.runtime/redmine-6.1.4` |
| Deploy automático | Desativado na consulta de 18/10/2026 |

A referência anterior deste README a Postgres separado estava incorreta.
O build remove e recria `.runtime`, que contém o banco SQLite configurado.
Portanto, não há preservação desse banco entre builds demonstrada por este
código. Antes de qualquer execução, confirmar se o conteúdo é exclusivamente
descartável de teste; dados a preservar exigem backup e restauração comprovados.
Não usar este perfil como armazenamento durável de tarefas ou como TODO canônico.

## Segurança e continuidade

O build baixa o arquivo oficial e valida seu SHA-256, mas permanece fixado em
6.1.4. Os avisos #44467 e #44468 exigem 6.1.5 na série 6.1 ou 7.0.2 na série 7.0.
A correção do gate ReqSys foi integrada pela PR #2763 no commit
`10051c1ed17177aaae9ea02ed36971856e4baa8c`; isso não atualiza este runtime.

A atualização não pode trocar apenas a versão do download: o caminho de
inicialização configurado no Render e a versão exportada ao E2E também estão
fixados em 6.1.4. Validar esses três pontos juntos para não criar uma falha de
inicialização ou uma evidência com versão declarada incorreta. O SHA do ReqSys
deve ser escolhido explicitamente, conferido no checkout e registrado na prova;
não substituir por uma referência flutuante nem reaproveitar evidência antiga.

Fontes oficiais revalidadas em 18/10/2026:
- https://www.redmine.org/projects/redmine/wiki/Download
- https://www.redmine.org/projects/redmine/wiki/Security_Advisories

## Identidade e efeitos do bootstrap

`bootstrap.rb` habilita REST API e reconcilia projeto privado, usuário de serviço,
token e associação a uma função regular. A chave vem da referência de ambiente
`REQSYS_REDMINE_API_KEY`; nunca registrar seu valor em código, logs ou evidências.
A execução desse bootstrap tem efeitos de escrita e não é um preflight de leitura.

O build usa o ID de projeto 1 no E2E, enquanto o bootstrap resolve o projeto pelo
identificador. Antes de usar um banco preservado, comprovar que ambos apontam para
o mesmo projeto; não assumir que o ID permanece 1.

## Evidência e critério de aceite

O arquivo `public/reqsys-e2e/evidence.json` é produzido durante o build. Sua
existência não prova saúde atual, persistência após reinício, o SHA atualmente
publicado nem integração com o PC24x7.

Antes de considerar a recuperação concluída, exigir no mesmo ambiente e SHA:
versão corrigida observada no servidor; banco e projeto identificados; prontidão
após a publicação; ida e volta ReqSys/Redmine com leitura independente; controle
negativo; replay sem duplicação; e comportamento de retentativa/quarentena.
Validar também a ausência de segredos na evidência efetivamente publicada.

O último build consultado, `dep-dathve893c1s73am6ua0`, terminou como
`build_failed` em 29/09/2026. A consulta aos logs dessa janela retornou vazia.
A causa específica dessa falha continua não comprovada; não atribuí-la apenas
ao SHA antigo nem repetir o deploy sem corrigir e validar as pré-condições.

Esta revisão corrige somente a documentação. Não altera build, banco, segredos,
versão instalada, comando de inicialização ou configuração do serviço.
