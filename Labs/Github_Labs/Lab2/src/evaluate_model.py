import os, json, pickle
from sklearn.metrics import f1_score, accuracy_score
import joblib
import argparse

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", type=str, required=True, help="Timestamp from GitHub Actions")
    args = parser.parse_args()

    timestamp = args.timestamp
    try:
        model = joblib.load(f'model_{timestamp}_dt_model.joblib')
    except Exception:
        raise ValueError('Failed to load the latest model')

    # held-out split saved by train_model.py
    try:
        with open('data/data.pickle', 'rb') as f:
            X = pickle.load(f)
        with open('data/target.pickle', 'rb') as f:
            y = pickle.load(f)
    except Exception:
        raise ValueError('Failed to load the test data')

    y_predict = model.predict(X)
    metrics = {"F1_Score": f1_score(y, y_predict),
               "Accuracy": accuracy_score(y, y_predict)}
    print(metrics)

    os.makedirs("metrics/", exist_ok=True)

    with open(f'{timestamp}_metrics.json', 'w') as metrics_file:
        json.dump(metrics, metrics_file, indent=4)
