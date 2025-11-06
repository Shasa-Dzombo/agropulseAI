import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
import numpy as np
import os

def plot_confusion_matrix(y_true, y_pred, classes, model_name):
    """
    Plots and saves a confusion matrix.
    """
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
    plt.title(f'Confusion Matrix for {model_name}')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    
    # Save the plot
    eval_dir = os.path.dirname(__file__)
    plot_path = os.path.join(eval_dir, f'{model_name}_confusion_matrix.png')
    plt.savefig(plot_path)
    print(f"Saved confusion matrix to {plot_path}")
    plt.close()

def save_classification_report(y_true, y_pred, classes, model_name):
    """
    Saves the classification report to a text file.
    """
    report = classification_report(y_true, y_pred, target_names=classes)
    
    eval_dir = os.path.dirname(__file__)
    report_path = os.path.join(eval_dir, f'{model_name}_classification_report.txt')
    with open(report_path, 'w') as f:
        f.write(f"Classification Report for {model_name}:\n\n")
        f.write(report)
    print(f"Saved classification report to {report_path}")

# This module is intended to be used by the training script,
# but you can add a main block to run evaluations independently if needed.
