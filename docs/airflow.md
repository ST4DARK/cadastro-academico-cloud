# Operação do Airflow

Ambiente local de desenvolvimento e apresentação: Airflow 3.4.0 standalone em Docker, com metadados SQLite em volume persistente. O Supabase permanece separado desse banco de metadados.

## Iniciar

Com Docker Desktop iniciado e .env preenchido, execute na raiz do repositório:

```powershell
docker compose --profile validacao up -d --build
docker compose ps
```

A interface fica em http://localhost:8080, disponível apenas no computador local. Aguarde o serviço ficar healthy.

Usuário: admin. Para consultar somente a senha gerada, sem confundir com a senha do Supabase:

```powershell
docker compose exec airflow python -c "import json; print(json.load(open('/opt/airflow/simple_auth_manager_passwords.json.generated'))['admin'])"
```

Use somente o valor da senha no formulário de login.

## Executar e acompanhar

Abra cadastro_academico_supabase e clique em Trigger DAG. Se estiver pausada, despause antes de executar.

| Configuração | Valor |
|---|---|
| Agenda | Manual, schedule=None |
| Tarefa | ingerir_dados |
| Execuções simultâneas da DAG | 1 |
| Novas tentativas após falha | 2 |
| Intervalo entre tentativas | 2 minutos |
| Limite por tentativa | 10 minutos |
| Processos locais do executor | Até 2 |

Acesse a execução → tarefa ingerir_dados → Logs na interface. As etapas e contagens aparecem como INFO. Falhas aparecem como ERROR, com etapa, identificação da ingestão, classe do erro, SQLSTATE quando disponível e pilha de execução. O resumo também é salvo em ingestoes.mensagem_erro quando o banco está acessível. O status success confirma a execução da tarefa; a tabela ingestoes também registra o resultado da carga.

Comandos úteis:

```powershell
docker compose exec airflow airflow dags list-import-errors
docker compose exec airflow airflow dags list-runs cadastro_academico_supabase --output json
```

Os logs gerais também estão disponíveis com docker compose logs -f airflow. A primeira inicialização pode imprimir a senha gerada, por isso revise o conteúdo antes de compartilhar capturas ou logs.

## Alterar o código

A DAG, o pacote Python e o .env são montados somente para leitura no container. A configuração é interpretada pelo Python sem interpolar caracteres especiais da senha. O .env não entra no contexto de construção da imagem.

O processador do Airflow identifica alterações no arquivo da DAG. Edições do pacote Python são usadas nas próximas execuções. Se alterar requirements.txt ou Dockerfile, reconstrua a imagem:

```powershell
docker compose --profile validacao up -d --build
```

## Parar

```powershell
docker compose --profile validacao down
```

Esse comando preserva o volume com os metadados e logs. Evite down --volumes ao fazer uma parada normal, pois ele apaga esse histórico local.

## Verificação já realizada

A execução validacao_airflow_001 terminou com status success, e a ingestão correspondente no Supabase foi concluída com 50 perfis. Scheduler, processador de DAGs, triggerer e banco de metadados foram conferidos como saudáveis.

Referências: [Quick Start](https://airflow.apache.org/docs/apache-airflow/stable/start.html) e [imagem Docker do Airflow](https://airflow.apache.org/docs/docker-stack/build.html).

## Backup e restauração

A DAG backup_academico_supabase contém criar_backup e restaurar_e_validar. Use o perfil validacao do Compose para manter o PostgreSQL local disponível. As tarefas operam em cópias locais; a fonte no Supabase não é destino de restauração. Consulte [o roteiro de segurança e backup](seguranca_backup.md).
