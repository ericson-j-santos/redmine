# Contrato de diff Git — TODO-7

Base do diagnóstico: d9ba2059cb0bf9cfc2c563a715133a0df55ce206, Tests
39315539687. Os jobs SQLite em Ruby 3.3 e 3.4 executaram 5699 casos e
falharam somente em GitAdapterTest#test_diff_path_invalid. Git 2.55.0
devolveu metadados do commit sem patch para um caminho inexistente.

O adaptador normaliza a saída sem cabeçalho de patch no ramo de revisão
única para uma lista vazia. Saídas com diff --git, --cc ou --combined
são preservadas integralmente. A comparação entre revisões e o retorno nil
para erro do comando permanecem no caminho original. Os três testes de
download que exigem o cabeçalho de commit continuam ativos.

Regressões reais cobrem caminho inexistente, arquivo existente sem mudança,
patch com metadados, comparação, repetição, commit raiz e revisão inválida.
O workflow Tests verifica o objeto da fixture, sintaxe e o resumo da suíte
direcionada: zero falhas, erros e skips, com pelo menos cinco casos.
A suíte ampla permanece obrigatória após a verificação direcionada.

A normalização reconhece os cabeçalhos emitidos pelo Git no formato normal.
Não é um parser universal de mensagens de tags anotadas ou de formatos
pretty personalizados: texto livre que imite um patch permanece uma limitação
preexistente. Não usar UnifiedDiff como detector: diffs binários, de modo e
combinados não exigem hunks textuais comuns.

Os resultados pertencem ao CI do novo SHA; este documento não antecipa aprovação.
Sem implantação, credenciais, privilégios ou bancos persistentes alterados.
Reversão: reverter somente este incremento na mesma branch.
