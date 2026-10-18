# File: src/model_development.py
import os
import json
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

WORKING_DIR = "/opt/airflow/working_data"
MODEL_DIR = "/opt/airflow/model"
os.makedirs(WORKING_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# a wine counts as "good" if tasters gave it 7 or more out of 10
GOOD_WINE_THRESHOLD = 7
METRICS_FILE = os.path.join(MODEL_DIR, "metrics.json")


def load_data() -> str:
    """
    Read the red wine quality CSV and pickle the raw dataframe.
    Returns path to saved file.
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "winequality-red.csv",
    )
    df = pd.read_csv(csv_path, sep=";")
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]

    out_path = os.path.join(WORKING_DIR, "raw.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(df, f)
    print(f"Loaded {len(df)} wines with {df.shape[1]} columns")
    return out_path


def validate_data(file_path: str) -> str:
    """
    Basic sanity checks: no missing values, quality in range.
    Drops duplicate rows and re-saves. Fails the task if checks don't pass.
    """
    with open(file_path, "rb") as f:
        df = pickle.load(f)

    if df.isnull().values.any():
        raise ValueError("Dataset has missing values")
    if not df["quality"].between(0, 10).all():
        raise ValueError("Quality scores outside 0-10")

    before = len(df)
    df = df.drop_duplicates()
    print(f"Dropped {before - len(df)} duplicate rows, {len(df)} left")

    out_path = os.path.join(WORKING_DIR, "validated.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(df, f)
    return out_path


def data_preprocessing(file_path: str) -> str:
    """
    Build the binary target, do a stratified split, scale features,
    and save (X_train, X_test, y_train, y_test) to pickle.
    """
    with open(file_path, "rb") as f:
        df = pickle.load(f)

    y = (df["quality"] >= GOOD_WINE_THRESHOLD).astype(int)
    X = df.drop(columns=["quality"])
    print(f"Good wines: {y.sum()} / {len(y)} ({y.mean():.1%})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=7, stratify=y
    )

    scaler = StandardScaler()
    X_train_tr = scaler.fit_transform(X_train)
    X_test_tr = scaler.transform(X_test)

    out_path = os.path.join(WORKING_DIR, "preprocessed.pkl")
    with open(out_path, "wb") as f:
        pickle.dump((X_train_tr, X_test_tr, y_train.values, y_test.values), f)
    return out_path


def build_model(file_path: str, filename: str) -> str:
    """
    Train a random forest and save to MODEL_DIR/filename. Returns model path.
    """
    with open(file_path, "rb") as f:
        X_train, X_test, y_train, y_test = pickle.load(f)

    # class_weight balanced since good wines are only ~13% of the data
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        class_weight="balanced",
        random_state=7,
    )
    model.fit(X_train, y_train)

    model_path = os.path.join(MODEL_DIR, filename)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    return model_path


def evaluate_model(file_path: str, filename: str) -> dict:
    """
    Load the saved model, score it on the test set, write metrics.json
    and return the metrics (ends up in XCom).
    """
    with open(file_path, "rb") as f:
        X_train, X_test, y_train, y_test = pickle.load(f)

    model_path = os.path.join(MODEL_DIR, filename)
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "f1": round(float(f1_score(y_test, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "test_size": int(len(y_test)),
        "good_wines_predicted": int(pred.sum()),
    }
    print(f"Test metrics: {metrics}")

    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics
