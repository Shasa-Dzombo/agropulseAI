import pandas as pd
import joblib
import os

def predict_crop(data):
    """
    Predicts the best crop for a given set of input features.
    
    Args:
        data (dict): A dictionary of input features.
        
    Returns:
        str: The recommended crop name.
    """
    # Load model, scaler, and encoder
    model_dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(model_dir, 'crop_recommendation_model.pkl'))
    scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))
    label_encoder = joblib.load(os.path.join(model_dir, 'label_encoder.pkl'))

    # Create a DataFrame from the input data
    df = pd.DataFrame([data])

    # Pre-process and engineer features (must match training)
    # This is a simplified version. A robust pipeline would have a shared feature engineering function.
    df['n_p_ratio'] = df['nitrogen'] / (df['phosphorus'] + 1e-6)
    df['n_k_ratio'] = df['nitrogen'] / (df['potassium'] + 1e-6)
    df['p_k_ratio'] = df['phosphorus'] / (df['potassium'] + 1e-6)
    df['nitrogen_sq'] = df['nitrogen']**2
    df['phosphorus_sq'] = df['phosphorus']**2
    df['potassium_sq'] = df['potassium']**2
    df['temp_category'] = pd.cut(df['temperature'], bins=[-10, 0, 10, 20, 30, 40, 50], labels=['freezing', 'cold', 'mild', 'warm', 'hot', 'very_hot'])
    df['rainfall_category'] = pd.cut(df['rainfall'], bins=[0, 100, 200, 300, 400], labels=['low', 'medium', 'high', 'very_high'])
    df = pd.get_dummies(df, columns=['temp_category', 'rainfall_category'], drop_first=True)

    # Align columns with the training set
    # This is a crucial step to handle missing columns after one-hot encoding
    training_cols = scaler.feature_names_in_
    df_aligned = df.reindex(columns=training_cols, fill_value=0)

    # Scale the features
    scaled_features = scaler.transform(df_aligned)

    # Make prediction
    prediction_encoded = model.predict(scaled_features)
    
    # Decode the prediction
    prediction_crop = label_encoder.inverse_transform(prediction_encoded)
    
    return prediction_crop[0]

if __name__ == '__main__':
    # Example usage
    sample_data = {
        'nitrogen': 90,
        'phosphorus': 45,
        'potassium': 45,
        'temperature': 22,
        'humidity': 80,
        'ph': 6.5,
        'rainfall': 200,
        'soil_moisture': 60
    }
    
    recommended_crop = predict_crop(sample_data)
    print(f"Based on the input data, the recommended crop is: {recommended_crop}")
