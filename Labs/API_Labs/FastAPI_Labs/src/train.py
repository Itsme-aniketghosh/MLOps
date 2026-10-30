from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report
import joblib
from data import load_data, split_data

def fit_model(X_train, y_train):
    """
    Train a Decision Tree Classifier and save the model to a file.
    Args:
        X_train (numpy.ndarray): Training features.
        y_train (numpy.ndarray): Training target values.
    """
    # only ~8% of Pokemon are legendary, so weight the rare class up
    dt_classifier = DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=12)
    dt_classifier.fit(X_train, y_train)
    joblib.dump(dt_classifier, "../model/pokemon_model.pkl")
    return dt_classifier

if __name__ == "__main__":
    X, y = load_data()
    X_train, X_test, y_train, y_test = split_data(X, y)
    model = fit_model(X_train, y_train)
    print(classification_report(y_test, model.predict(X_test), target_names=["mid", "legendary"]))
