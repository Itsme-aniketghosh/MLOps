import pandas as pd
from sklearn.model_selection import train_test_split

FEATURES = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]

def load_data():
    """
    Load the Pokemon stats dataset and return the features and target values.
    Returns:
        X (numpy.ndarray): Base stats of each Pokemon.
        y (numpy.ndarray): 1 if the Pokemon is legendary, 0 if it is mid.
    """
    df = pd.read_csv("../data/pokemon.csv")
    X = df[FEATURES].values
    y = df["Legendary"].astype(int).values
    return X, y

def split_data(X, y):
    """
    Split the data into training and testing sets.
    Args:
        X (numpy.ndarray): The features of the dataset.
        y (numpy.ndarray): The target values of the dataset.
    Returns:
        X_train, X_test, y_train, y_test (tuple): The split dataset.
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=12, stratify=y)
    return X_train, X_test, y_train, y_test
