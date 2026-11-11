# Cadastro Acadêmico Cloud

Projeto acadêmico de banco de dados na nuvem com **PostgreSQL/Supabase**, **pandas** e **Apache Airflow**.

A pipeline busca 50 perfis brasileiros fictícios na Random User, valida os dados, cria DataFrames e grava alunos, cursos e matrículas. Cada execução fica registrada em ingestoes. A carga já foi validada pelo Airflow, inclusive com reexecução sem duplicações.

## Estrutura

```text
cadastro_academico/  Código Python da pipeline e da conexão
dags/              DAGs de ingestão e backup do Airflow
supabase/          Estrutura SQL de referência
docs/              Arquitetura, operação, segurança e backup
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

## Segurança e backup

Consulte [controle de acesso e backup](docs/seguranca_backup.md) para provisionar as contas de leitor, operador e pipeline. As senhas ficam apenas no `.env`.

A DAG `backup_academico_supabase` cria uma cópia consistente e testa a restauração em um PostgreSQL local separado. Os arquivos `.dump`, `.manifest.json` e `.restore.json` ficam em `backups/`, fora do Git. A validação confere contagens, hashes dos registros e RLS nas quatro tabelas.

## Arquivos locais

`.env`, `.venv`, caches, backups e materiais de entrega ficam fora do Git. As credenciais não entram na imagem Docker. Use apenas dados fictícios; não registre senhas no código nem no histórico das cargas.
