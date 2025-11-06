import pandas as pd
import numpy as np

def build_features(df):
    """
    Engineers new features from the existing data to improve model performance.
    """
    print("Building advanced features...")

    # Interaction features
    df['n_p_ratio'] = df['nitrogen'] / (df['phosphorus'] + 1e-6)
    df['n_k_ratio'] = df['nitrogen'] / (df['potassium'] + 1e-6)
    df['p_k_ratio'] = df['phosphorus'] / (df['potassium'] + 1e-6)
    
    # Polynomial features for key nutrients
    df['nitrogen_sq'] = df['nitrogen']**2
    df['phosphorus_sq'] = df['phosphorus']**2
    df['potassium_sq'] = df['potassium']**2

    # Binning temperature and rainfall
    df['temp_category'] = pd.cut(df['temperature'], bins=[-10, 0, 10, 20, 30, 40, 50], labels=['freezing', 'cold', 'mild', 'warm', 'hot', 'very_hot'])
    df['rainfall_category'] = pd.cut(df['rainfall'], bins=[0, 100, 200, 300, 400], labels=['low', 'medium', 'high', 'very_high'])

    # One-hot encode categorical features
    df = pd.get_dummies(df, columns=['temp_category', 'rainfall_category'], drop_first=True)

    print("Feature engineering complete.")
    return df
