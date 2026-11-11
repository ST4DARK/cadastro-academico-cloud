# Arquitetura

Fluxo: **Airflow → Random User → validação → DataFrames pandas → PostgreSQL/Supabase**.

## Responsabilidades

| Módulo | Responsabilidade |
|---|---|
| dags/ingestao_academica.py | Define a DAG e suas tentativas, limite de tempo e concorrência |
| cadastro_academico/configuracao.py | Define parâmetros da fonte e o caminho do .env |
| cadastro_academico/fonte.py | Consulta a API Random User |
| cadastro_academico/transformacao.py | Valida os perfis e simula cursos e matrículas |
| cadastro_academico/quadros.py | Cria os DataFrames e confere duplicações e referências |
| cadastro_academico/banco.py | Abre conexões PostgreSQL usando o .env |
| cadastro_academico/gravacao.py | Executa UPSERTs, resolve IDs e mantém o histórico |
| cadastro_academico/pipeline.py | Coordena a execução e trata falhas |

## Fonte e DataFrames

A fonte é a API [Random User](https://randomuser.me/documentation), versão 1.4. Nacionalidade brasileira, seed, página e quantidade estão fixas para repetir o conjunto de teste.

- alunos: codigo_origem, nome e email.
- cursos: nome.
- matriculas: numero_matricula, aluno_codigo_origem e curso_nome.

O codigo_origem usa login.uuid com prefixo randomuser:. Curso e matrícula são simulados de forma determinística a partir desse UUID. A mudança de ordem da resposta não troca os vínculos. Outros campos do bloco login não são persistidos.

Os DataFrames ficam em memória na tarefa do Airflow, sem passar por XCom. Não existe arquivo JSON intermediário.

## Gravação e reexecução

1. Cria um registro em ingestoes com status em_andamento, antes de consultar a fonte.
2. Busca e valida os perfis, depois cria os DataFrames.
3. Dentro de uma transação, grava cursos e alunos.
4. Combina os DataFrames com os IDs devolvidos pelo banco para resolver id_aluno e id_curso.
5. Grava matrículas, marca a ingestão como concluida e confirma a transação.

Cursos são identificados pelo nome; alunos pelo código de origem; matrículas pelo par aluno/curso. Uma reexecução atualiza nome/e-mail dos alunos que mudaram, preserva IDs e mantém vínculos existentes, incluindo matrículas canceladas. Não há exclusão de registros ausentes na fonte.

quantidade_registros_gravados conta alunos confirmados no banco, inclusive os que já existiam; não significa novas inserções.

## Falhas e logs

A execução é iniciada pela DAG do Airflow. Logs INFO informam as etapas e as contagens. Logs ERROR mostram a etapa, o identificador da ingestão, a classe do erro, o SQLSTATE quando houver e a pilha de execução sem a mensagem bruta da exceção. Não são registrados senha nem conteúdo dos perfis.


Uma falha na carga desfaz o lote inteiro, incluindo a atualização de conclusão do histórico. Em seguida, o histórico é marcado como falhou, com classe do erro e SQLSTATE quando disponível. A pipeline não registra senha nem o conteúdo completo do lote.

Se a conexão inicial falhar, não será possível criar o histórico. Em caso de interrupção do processo ou perda de conexão, o registro pode precisar de conferência manual.

A DAG transforma o código de erro da pipeline em falha da tarefa. Cada nova tentativa abre outra ingestão, e a repetição da carga não duplica os vínculos.

## Persistência e acesso

Os dados acadêmicos ficam no Supabase. O volume Docker airflow-data guarda apenas os metadados, logs e credenciais locais do Airflow.

O RLS está ativo nas quatro tabelas. A carga usa academico_ingestor, vinculada ao perfil restrito academico_pipeline. Leitor e operador usam contas próprias; as políticas e a rotina de backup/restauração estão documentadas em seguranca_backup.md.

O schema modela um vínculo por par aluno/curso. Rematrículas por semestre não fazem parte desta versão.

## Backup e evidências

A DAG backup_academico_supabase exporta o schema public em snapshot consistente e restaura a cópia em um PostgreSQL Docker separado. O módulo backup.py confere os hashes e as contagens; evidencias.py consolida os resultados sanitizados em entrega/evidencias.json. O relatório é gerado a partir dessas evidências.
