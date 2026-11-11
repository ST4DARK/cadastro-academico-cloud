# Controle de acesso, backup e entrega

## Estado validado

- Três contas PostgreSQL reais: leitor, operador e pipeline, sem superusuário, criação de roles/bancos ou bypass de RLS.
- Leitura permitida aos três perfis; alteração de aluno bloqueada para leitor e permitida para operador/pipeline.
- Exclusão de dados e criação de tabelas bloqueadas para os três perfis.
- RLS ativo em quatro tabelas, com 12 políticas. anon e authenticated continuam bloqueados.
- Ingestão validada com a conta restrita da pipeline.
- Backup exportado e restaurado em um banco PostgreSQL local separado; quatro hashes e contagens idênticos.
- Relatório Word e PDF e capturas reais das DAGs disponíveis em entrega/.

## Credenciais e perfis

Os campos SUPABASE_DB_* ou DATABASE_URL são a conexão administrativa, usada no provisionamento e backup. A pipeline usa PIPELINE_DB_USER/PASSWORD; as demonstrações usam LEITOR_DB_USER/PASSWORD e OPERADOR_DB_USER/PASSWORD. RESTORE_DB_PASSWORD protege somente o PostgreSQL local de validação. As senhas ficam apenas no .env.

Os perfis são usuários do PostgreSQL. Não são usuários de Supabase Auth, nem usuários do painel Airflow. Cada mecanismo protege um acesso diferente.

| Perfil | Dados acadêmicos | Histórico | Exclusão / DDL |
|---|---|---|---|
| Leitor | Consultar | Consultar | Bloqueados |
| Operador | Consultar, cadastrar e alterar | Consultar | Bloqueados |
| Pipeline | Consultar e carregar o lote | Consultar, inserir e finalizar | Bloqueados |

Cursos e matrículas existentes não são atualizados pela conta da pipeline; alunos podem ser atualizados. Os privilégios exatos estão em supabase/migrations/20261111000100_controle_acesso.sql.

O provisionamento já foi executado. Para reproduzir em outro projeto Supabase com o schema inicial criado, preencha a conexão administrativa, instale requirements.txt na .venv e execute localmente:

```powershell
.\.venv\Scripts\python.exe -c "from cadastro_academico.acesso import configurar_contas, verificar_acessos; configurar_contas(); verificar_acessos()"
```

A rotina aplica a migração, gera ou reaproveita senhas e salva o resultado no .env. Ela é de manutenção administrativa; a execução da pipeline permanece no Airflow. Os testes de alteração usam ROLLBACK e não mantêm mudanças nos alunos.

## Backup e restauração

Inicie o ambiente com o PostgreSQL de validação:

```powershell
docker compose --profile validacao up -d --build
```

No Airflow, use a DAG backup_academico_supabase. Ela executa criar_backup e depois restaurar_e_validar. A agenda é manual. A DAG de ingestão continua sendo cadastro_academico_supabase.

O pg_dump usa um snapshot consistente da conexão administrativa. Os arquivos .dump e .manifest.json ficam em backups/, fora do Git. O manifesto contém hashes SHA-256 do arquivo e dos registros das quatro tabelas.

O pg_restore recupera a cópia em um banco novo no serviço postgres-restauracao, sem porta publicada no host. A rotina não aceita um host de destino externo. As políticas e privilégios são reaplicados, e todos os registros são comparados com o snapshot por contagem e hash canônico em UTC. O último banco aprovado aparece em entrega/evidencias.json.

O escopo é o schema public da aplicação, não os serviços Auth, Storage ou as senhas globais do Supabase. O PostgreSQL de validação é independente do banco de metadados do Airflow e do Supabase.

Para parar preservando arquivos e volumes:

```powershell
docker compose --profile validacao down
```

Não use --volumes durante uma parada normal se quiser manter as evidências e o banco local recuperado. Preserve também os arquivos de backups/; o histórico do Airflow não substitui esses arquivos.

## Apresentar a atividade

1. Abra a DAG de ingestão e mostre uma execução success e seus logs de etapas e contagens.
2. Mostre as quatro tabelas no Supabase e a matriz de permissões em entrega/evidencias.json.
3. Na DAG de backup, mostre criar_backup e restaurar_e_validar com sucesso.
4. Abra o manifesto do backup e a evidência de restauração: contagens e hashes devem coincidir.
5. Entregue o PDF ou o Word, após preencher professor, turma e demais integrantes na capa. Não compartilhe o .env.

## Gerar novamente o relatório

As bibliotecas de relatório são opcionais, separadas das dependências da pipeline:

```powershell
.\.venv\Scripts\python.exe -m pip install -r docs/requirements.txt
.\.venv\Scripts\python.exe docs/capturar_evidencias.py
.\.venv\Scripts\python.exe docs/gerar_relatorio.py
```

A captura usa uma sessão temporária do Edge e não salva senha nem token. O gerador usa entrega/evidencias.json para criar entrega/relatorio.docx e entrega/relatorio.pdf. As capturas ficam em entrega/evidencias/.
