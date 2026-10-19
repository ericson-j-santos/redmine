# Recuperação do lint e da cobertura de miniaturas — 19/10/2026

Continuidade: ReqSys issue #1686 / TODO-7. Alterações somente na branch DEV
existente. Não autoriza implantação nem acesso a dados persistentes.

## Causas reproduzidas nos logs do SHA 570ed959

O lint encontrou blocos RSpec colados em `projects_spec.rb`, além de espaços,
cabeçalhos, modo do script com shebang, interpolação redundante e declaração
duplicada de pg. A correção preserva os testes, o driver pg global, as opções de
autenticação e o conteúdo dos documentos. Os scripts `criar_documentos.rb` e
`setup_trackers.rb` não são executados contra dados; somente parse/lint.

O único skip do Attachment upstream corresponde a
`test_thumbnailable_should_be_true_for_images`: depende de convert_installed?.
O executor agora instala ImageMagick pelo gerenciador assinado da imagem Ubuntu
em runner hospedado descartável, com limites de tempo, e produz JPEG/WebP 4x4
reais para leitura independente com identify. Não altera política de formatos,
serviço Render, host físico, secrets ou assinatura.

O job integral exige resumos únicos de Attachment e Mailer, execução efetiva,
zero falhas, erros e skips. O verificador anterior de compatibilidade continua
produzindo seus detalhes; este gate adicional rejeita qualquer skip antes da
aprovação final do job. O build standalone não é apresentado como prova deste
gate CI nem como autorização de publicação.

## Prevenção e validação

O lint completo permanece ativo, precedido de ruby -c e controle negativo do
parser para a junção inválida. Cinco testes do novo gate cobrem resultado
positivo, replay, resumo antigo com um skip, logs inválidos/ausentes/duplicados,
erros/falhas e ausência de suite. Remover a rejeição de skips causou duas falhas
no controle isolado; restaurado o gate, os cinco testes passaram.

A confirmação de Ruby, ImageMagick, lint integral, suites upstream e lifecycle
real pertence ao CI do novo commit. Este documento não antecipa resultados.

## Auditoria da raiz permanece bloqueante

O Gemfile.lock histórico da raiz contém Rails 8.0.3 e várias outras famílias
reprovadas. A raiz NÃO usa o bundle Rails 7.2.4 do runtime baixado. Não copiar
um lock sobre o outro, não relaxar auditoria e não declarar o workflow verde
antes da resolução compatível e versionada das dependências da raiz.

Dados/backup/restauração ou descarte autorizado, E2E publicado, PC24x7 e projeção
TODO Global continuam pendentes. Rollback: reverter o incremento na mesma
branch; o rollback não autoriza reutilizar bundle vulnerável.
