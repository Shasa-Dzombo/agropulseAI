import pandas as pd
import os

def load_data(file_path='../data/raw_data.csv'):
    """
    Loads data from a CSV file.
    """
    path = os.path.join(os.path.dirname(__file__), file_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found at {path}. Please run generate_data.py first.")
    
    print(f"Loading data from {path}...")
    df = pd.read_csv(path)
    return df
