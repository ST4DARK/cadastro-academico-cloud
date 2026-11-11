FROM apache/airflow:3.4.0-python3.12

COPY --chown=airflow:root requirements.txt /tmp/requirements-projeto.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.12.txt" \
    -r /tmp/requirements-projeto.txt

ENV PYTHONPATH=/opt/projeto
