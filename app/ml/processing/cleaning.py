from sklearn.impute import KNNImputer
import pandas as pd

def clean_data(df):
    """
    Cleans the dataframe by handling missing values and duplicates.
    """
    print("Cleaning data...")
    
    # Drop duplicates
    initial_rows = len(df)
    df.drop_duplicates(inplace=True)
    print(f"Removed {initial_rows - len(df)} duplicate rows.")

    # Handle missing values using KNNImputer for numerical columns
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
    
    if df[numerical_cols].isnull().sum().sum() > 0:
        print("Imputing missing values using KNNImputer...")
        imputer = KNNImputer(n_neighbors=5)
        df[numerical_cols] = imputer.fit_transform(df[numerical_cols])
    else:
        print("No missing numerical values to impute.")

    print("Data cleaning complete.")
    return df
