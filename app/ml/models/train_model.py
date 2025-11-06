import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report
import joblib
import os

# Import project modules
from app.ml.processing.loader import load_data
from app.ml.processing.cleaning import clean_data
from app.ml.features.build_features import build_features

def train_and_evaluate():
    """
    Main function to run the training and evaluation pipeline.
    """
    # 1. Load and Prepare Data
    df = load_data()
    df = clean_data(df)
    df = build_features(df)

    # 2. Encode Target Variable
    X = df.drop('crop', axis=1)
    y = df['crop']
    
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    # Save the encoder for later use in prediction
    model_dir = os.path.dirname(__file__)
    joblib.dump(label_encoder, os.path.join(model_dir, 'label_encoder.pkl'))

    # 3. Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

    # 4. Scale Features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Save the scaler
    joblib.dump(scaler, os.path.join(model_dir, 'scaler.pkl'))

    # 5. Define Models and Hyperparameter Grids
    models = {
        'RandomForest': (RandomForestClassifier(random_state=42), {
            'n_estimators': [100, 200],
            'max_depth': [10, 20, None],
            'min_samples_split': [2, 5]
        }),
        'GradientBoosting': (GradientBoostingClassifier(random_state=42), {
            'n_estimators': [100, 200],
            'learning_rate': [0.05, 0.1],
            'max_depth': [3, 5]
        }),
        'SVC': (SVC(probability=True, random_state=42), {
            'C': [0.1, 1, 10],
            'gamma': ['scale', 'auto']
        })
    }

    best_model = None
    best_score = 0
    best_model_name = ''

    # 6. Train, Tune, and Evaluate Models
    for name, (model, params) in models.items():
        print(f"--- Training {name} ---")
        grid_search = GridSearchCV(model, params, cv=3, n_jobs=-1, verbose=1, scoring='accuracy')
        grid_search.fit(X_train_scaled, y_train)

        print(f"Best parameters for {name}: {grid_search.best_params_}")
        
        model_best = grid_search.best_estimator_
        y_pred = model_best.predict(X_test_scaled)
        
        print(f"Classification Report for {name}:")
        report = classification_report(y_test, y_pred, target_names=label_encoder.classes_)
        print(report)

        if grid_search.best_score_ > best_score:
            best_score = grid_search.best_score_
            best_model = model_best
            best_model_name = name

    # 7. Save the Best Model
    print(f"\nBest model is {best_model_name} with accuracy {best_score:.4f}")
    model_path = os.path.join(model_dir, 'crop_recommendation_model.pkl')
    joblib.dump(best_model, model_path)
    print(f"Best model saved to {model_path}")

if __name__ == '__main__':
    train_and_evaluate()
