# Cadastro Acadêmico Cloud

Projeto acadêmico de banco de dados na nuvem com **PostgreSQL/Supabase**, **pandas** e **Apache Airflow**.

A pipeline busca 50 perfis brasileiros fictícios na Random User, valida os dados, cria DataFrames e grava alunos, cursos e matrículas. Cada execução fica registrada em ingestoes. A carga já foi validada pelo Airflow, inclusive com reexecução sem duplicações.

## Estrutura

```text
cadastro_academico/  Código Python da pipeline e da conexão
dags/              DAG do Airflow
supabase/          Estrutura SQL de referência
docs/              Arquitetura, operação e gerador do relatório
entrega/           Relatório Word/PDF e evidências reais
compose.yaml       Ambiente local do Airflow
Dockerfile         Imagem com as dependências da pipeline
requirements.txt   Dependências Python instaladas na imagem
.env.example       Modelo de configuração, sem credenciais
```

## Configuração

Crie `.env` a partir de `.env.example` apenas se ainda não existir. Preencha os dados de **Supabase → Connect → Session pooler**:

- SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME e SUPABASE_DB_USER.
- SUPABASE_DB_PASSWORD: senha do banco, mantida localmente.

Esses campos são administrativos. As contas restritas da pipeline e dos usuários foram geradas no provisionamento descrito em docs/seguranca_backup.md. Como alternativa, use DATABASE_URL, que tem prioridade quando preenchida. Nessa URI, caracteres especiais da senha precisam de percent-encoding; nos campos separados, use a senha literal. O login do MCP no Codex é independente dessas credenciais.

## Executar com Airflow

Requer Docker Desktop iniciado; no Windows, use o backend WSL2.

```powershell
docker compose --profile validacao up -d --build
```

Abra http://localhost:8080. Usuário: `admin`. Para consultar somente a senha gerada:

```powershell
docker compose exec airflow python -c "import json; print(json.load(open('/opt/airflow/simple_auth_manager_passwords.json.generated'))['admin'])"
```

Encontre `cadastro_academico_supabase`, despause se necessário e clique em **Trigger DAG**. A execução é manual e é iniciada pelo Airflow. Veja [operação do Airflow](docs/airflow.md) para acompanhar logs, execuções e parar o ambiente.

## Banco e arquitetura

| Tabela | Chave | Finalidade |
|---|---|---|
| alunos | id_aluno | Perfil fictício e código de origem |
| cursos | id_curso | Cadastro dos cursos |
| matriculas | id_matricula | Vínculo entre aluno e curso |
| ingestoes | id_ingestao | Histórico, status, contagens e horários |

O banco conectado já está criado. `supabase/schema.sql` serve para instalação do zero. Futuras alterações devem usar migrações incrementais.

Consulte [a arquitetura](docs/arquitetura.md) para entender os módulos, DataFrames, transações e a identificação dos perfis.

## Entregas da atividade

- [Relatório PDF](entrega/relatorio.pdf) e [Word editável](entrega/relatorio.docx), com capturas reais do Airflow.
- [Evidências de permissões, DAGs, backup e restauração](entrega/evidencias.json).
- [Controle de acesso, backup e roteiro de apresentação](docs/seguranca_backup.md).

Foram validados três perfis PostgreSQL e a ingestão com uma conta restrita. O backup foi restaurado em um PostgreSQL local separado, com contagens e hashes idênticos nas quatro tabelas. A DAG backup_academico_supabase permite repetir a prova de recuperação.

As senhas dos perfis e do banco de restauração são geradas no provisionamento e ficam apenas no .env. Consulte docs/seguranca_backup.md antes de configurar outro ambiente. A entrada da pipeline é o Airflow; o provisionamento é uma operação administrativa local.

Antes de entregar, complete professor, turma/unidade e demais integrantes na capa. O código e os entregáveis são versionados neste repositório; as DAGs usam acionamento manual.

## Arquivos locais

`.env`, `.venv`, caches e backups ficam fora do Git. As credenciais não entram na imagem Docker. Use apenas dados fictícios; não registre senhas no código nem no histórico das cargas.
