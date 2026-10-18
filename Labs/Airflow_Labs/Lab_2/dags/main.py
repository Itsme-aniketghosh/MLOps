# File: main.py
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.smtp.operators.smtp import EmailOperator
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.task.trigger_rule import TriggerRule

from src.model_development import (
    load_data,
    validate_data,
    data_preprocessing,
    build_model,
    evaluate_model,
)

MODEL_FILE = "wine_rf.sav"

# ---------- Default args ----------
default_args = {
    "owner": "Aniket Ghosh",
    "start_date": pendulum.datetime(2025, 1, 1, tz="UTC"),
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=1),
}

# ---------- DAG ----------
dag = DAG(
    dag_id="Wine_Quality_Pipeline",
    default_args=default_args,
    description="Train a random forest to flag good red wines (quality >= 7)",
    schedule="@weekly",
    catchup=False,
    tags=["wine", "classification", "lab2"],
    owner_links={"Aniket Ghosh": "mailto:ghosh.anik@northeastern.edu"},
    max_active_runs=1,
)

# ---------- Tasks ----------
start_task = BashOperator(
    task_id="start_pipeline",
    bash_command="echo 'Starting wine quality run for {{ ds }}'",
    dag=dag,
)

# needs smtp set up in airflow.cfg, see README
# send_email = EmailOperator(
#     task_id="send_email",
#     to="ghosh.anik@northeastern.edu",
#     subject="Wine quality model retrained",
#     html_content="<p>Metrics: {{ ti.xcom_pull(task_ids='evaluate_model_task') }}</p>",
#     dag=dag,
# )

load_data_task = PythonOperator(
    task_id="load_data_task",
    python_callable=load_data,
    dag=dag,
)

validate_data_task = PythonOperator(
    task_id="validate_data_task",
    python_callable=validate_data,
    op_args=[load_data_task.output],
    dag=dag,
)

data_preprocessing_task = PythonOperator(
    task_id="data_preprocessing_task",
    python_callable=data_preprocessing,
    op_args=[validate_data_task.output],
    dag=dag,
)

build_save_model_task = PythonOperator(
    task_id="build_save_model_task",
    python_callable=build_model,
    op_args=[data_preprocessing_task.output, MODEL_FILE],
    dag=dag,
)

evaluate_model_task = PythonOperator(
    task_id="evaluate_model_task",
    python_callable=evaluate_model,
    op_args=[data_preprocessing_task.output, MODEL_FILE],
    dag=dag,
)

# fire and forget so this DAG can finish cleanly
trigger_flask_task = TriggerDagRunOperator(
    task_id="trigger_flask_dashboard",
    trigger_dag_id="Wine_Quality_Flask",
    conf={"message": "Wine model run finished"},
    reset_dag_run=False,
    wait_for_completion=False,
    trigger_rule=TriggerRule.ALL_DONE,  # still run if something upstream fails
    dag=dag,
)

# ---------- Dependencies ----------
start_task >> load_data_task >> validate_data_task >> \
    data_preprocessing_task >> build_save_model_task >> \
    evaluate_model_task >> trigger_flask_task
