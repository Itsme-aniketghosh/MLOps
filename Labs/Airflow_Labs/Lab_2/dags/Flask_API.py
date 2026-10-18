from __future__ import annotations

import os
import json
import socket
import pendulum
import requests
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from flask import Flask, redirect, render_template, jsonify

# ---------- Config ----------
# WEBSERVER should point to 'airflow-apiserver' from the compose file
WEBSERVER = os.getenv("AIRFLOW_WEBSERVER", "http://airflow-apiserver:8080")
AF_USER   = os.getenv("AIRFLOW_USERNAME", "airflow")
AF_PASS   = os.getenv("AIRFLOW_PASSWORD", "airflow")
TARGET_DAG_ID = os.getenv("TARGET_DAG_ID", "Wine_Quality_Pipeline")
METRICS_FILE = "/opt/airflow/model/metrics.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# ---------- Flask app ----------
app = Flask(__name__, template_folder=TEMPLATE_DIR)


def load_metrics():
    try:
        with open(METRICS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def get_latest_run_info():
    url = f"{WEBSERVER}/api/v2/dags/{TARGET_DAG_ID}/dagRuns?order_by=-run_after&limit=1"

    info = {
        "dag_id": TARGET_DAG_ID,
        "state": "unknown",
        "run_id": "N/A",
        "logical_date": "N/A",
        "start_date": "N/A",
        "end_date": "N/A",
        "note": "",
    }

    try:
        # airflow 3 api wants a JWT, basic auth gets a 401
        tok = requests.post(
            f"{WEBSERVER}/auth/token",
            json={"username": AF_USER, "password": AF_PASS},
            timeout=10,
        )
        if not tok.ok:
            info["note"] = f"Login failed {tok.status_code}"
            return False, info
        headers = {"Accept": "application/json", "Authorization": f"Bearer {tok.json()['access_token']}"}

        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            info["note"] = f"API error {r.status_code}"
            return False, info

        runs = r.json().get("dag_runs", [])
        if not runs:
            info["note"] = "No runs yet for this DAG"
            return False, info

        run = runs[0]
        state = run.get("state", "unknown")
        info.update({
            "state": state,
            "run_id": run.get("dag_run_id", "N/A"),
            "logical_date": run.get("logical_date") or run.get("run_after", "N/A"),
            "start_date": run.get("start_date", "N/A"),
            "end_date": run.get("end_date", "N/A"),
        })

        # still going, don't call it a failure
        if state in ("queued", "running"):
            info["note"] = "Wine model is still training..."
            return False, info

        return state == "success", info

    except Exception as e:
        info["note"] = f"Network issue: {e}"
        return False, info


@app.route("/")
def index():
    ok, _ = get_latest_run_info()
    return redirect("/success" if ok else "/failure")


@app.route("/success")
def success():
    _, info = get_latest_run_info()
    return render_template("success.html", metrics=load_metrics(), **info)


@app.route("/failure")
def failure():
    _, info = get_latest_run_info()
    return render_template("failure.html", **info)


@app.route("/metrics")
def metrics():
    return jsonify(load_metrics())


@app.route("/health")
def health():
    return "ok", 200


def start_flask_app():
    """
    Starts the Flask server. Blocks the worker slot, reloader off for Docker.
    """
    # an earlier run may still be serving the page
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 5555)) == 0:
            print("Dashboard already running on port 5555, nothing to do")
            return

    print(f"Starting Flask on 0.0.0.0:5555, watching {TARGET_DAG_ID} at {WEBSERVER}", flush=True)
    app.run(host="0.0.0.0", port=5555, debug=False, use_reloader=False)


# ---------- DAG ----------
default_args = {
    "owner": "Aniket Ghosh",
    "start_date": pendulum.datetime(2025, 1, 1, tz="UTC"),
    "retries": 0,
}

dag = DAG(
    dag_id="Wine_Quality_Flask",
    default_args=default_args,
    description="Serves a status page for the latest wine model run",
    schedule=None,
    catchup=False,
    tags=["wine", "flask", "lab2"],
    is_paused_upon_creation=False,
)

PythonOperator(
    task_id="start_flask_dashboard",
    python_callable=start_flask_app,
    dag=dag,
)
