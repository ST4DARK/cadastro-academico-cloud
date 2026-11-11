"""Backup e prova de restauração sem alterar o banco de origem."""

from datetime import timedelta
import pendulum
from airflow.sdk import DAG, task

with DAG(
    dag_id="backup_academico_supabase",
    description="Backup consistente e restauração validada em PostgreSQL local",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    schedule=None, catchup=False, max_active_runs=1, tags=["academico", "backup"],
) as dag:

    @task(task_id="criar_backup", retries=1, retry_delay=timedelta(minutes=1), execution_timeout=timedelta(minutes=5))
    def exportar():
        from cadastro_academico.backup import criar_backup
        return criar_backup()

    @task(task_id="restaurar_e_validar", retries=1, retry_delay=timedelta(minutes=1), execution_timeout=timedelta(minutes=5), do_xcom_push=False)
    def validar(arquivo):
        from cadastro_academico.backup import restaurar_e_validar
        restaurar_e_validar(arquivo)

    validar(exportar())
