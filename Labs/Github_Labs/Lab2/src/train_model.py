import mlflow, datetime, os, pickle
from joblib import dump
from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, f1_score
import argparse

DATASET = "raquiba/Sarcasm_News_Headline"


def load_data():
    # onion (1) vs huffpost (0) headlines
    df = load_dataset(DATASET, split="train").to_pandas()
    df = df.drop_duplicates(subset="headline")
    return train_test_split(df["headline"], df["is_sarcastic"],
                            test_size=0.2, random_state=42, stratify=df["is_sarcastic"])


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", type=str, required=True, help="Timestamp from GitHub Actions")
    args = parser.parse_args()

    timestamp = args.timestamp
    print(f"Timestamp received from GitHub Actions: {timestamp}")

    X_train, X_test, y_train, y_test = load_data()

    os.makedirs('data', exist_ok=True)
    with open('data/data.pickle', 'wb') as f:
        pickle.dump(X_test, f)
    with open('data/target.pickle', 'wb') as f:
        pickle.dump(y_test, f)

    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    dataset_name = "Onion vs HuffPost"
    current_time = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    experiment_id = mlflow.create_experiment(f"{dataset_name}_{current_time}")

    with mlflow.start_run(experiment_id=experiment_id, run_name=dataset_name):

        mlflow.log_params({
            "dataset_name": DATASET,
            "train_size": len(X_train),
            "test_size": len(X_test)})

        model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            LogisticRegression(max_iter=1000, C=5),
        )
        model.fit(X_train, y_train)

        y_predict = model.predict(X_test)
        mlflow.log_metrics({'Accuracy': accuracy_score(y_test, y_predict),
                            'F1 Score': f1_score(y_test, y_predict)})

        # quick sanity check on a couple of headlines
        for h in ["area man still not sure what he does at work",
                  "senate passes infrastructure bill"]:
            print(f"{h!r} -> onion: {model.predict_proba([h])[0][1]:.2f}")

        model_filename = f'model_{timestamp}_dt_model.joblib'
        dump(model, model_filename)
