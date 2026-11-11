"""Orquestra a carga acadêmica no Airflow 3."""

from datetime import timedelta

import pendulum
from airflow.sdk import DAG, task

with DAG(
    dag_id="cadastro_academico_supabase",
    description="Random User → DataFrames → Supabase",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["academico", "supabase"],
) as dag:

    @task(
        task_id="ingerir_dados",
        retries=2,
        retry_delay=timedelta(minutes=2),
        execution_timeout=timedelta(minutes=10),
        do_xcom_push=False,
    )
    def ingerir_dados():
        # Acesso à API e ao banco ocorre somente durante a execução da tarefa.
        from cadastro_academico.pipeline import executar_pipeline

        if executar_pipeline() != 0:
            raise RuntimeError("A ingestão falhou. Confira os logs e a tabela ingestoes.")

    ingerir_dados()
