"""
ml/train.py
Decision Tree Classifier Training for Supply Chain Risk Level Prediction.
Produces: accuracy, precision, recall, F1 score, confusion matrix, feature importance.
Saves: risk_classifier.joblib, encoders.joblib, model_metrics.json
"""

import os
import json
import joblib
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)
from sklearn.preprocessing import LabelEncoder
from backend.config import Config

logger = logging.getLogger(__name__)


def train_model():
    """
    Full Decision Tree training pipeline.
    Reads the DataCo CSV, engineers features, trains and evaluates the model,
    and saves model artifacts + metrics to disk.
    """
    logger.info("Starting Decision Tree model training...")

    # 1. Load Dataset
    csv_path = Config.DATASET_PATH
    if not os.path.exists(csv_path):
        logger.warning(f"Dataset not found at {csv_path}. Generating mock data...")
        from backend.etl.generate_mock_data import generate_data
        generate_data(18500)

    df = pd.read_csv(csv_path, encoding="utf-8")
    logger.info(f"Loaded {len(df)} records from dataset.")

    # 2. Clean Data
    df = df.dropna(subset=["Order Id", "Customer Id", "Product Card Id"])

    # 3. Feature Engineering
    df["Delivery_Delay"] = (
        df["Days for shipping (real)"].fillna(0).astype(int) -
        df["Days for shipment (scheduled)"].fillna(0).astype(int)
    )

    def calculate_risk(row):
        delay = row["Delivery_Delay"]
        profit = row.get("Benefit per order", 0)
        if delay > 0 and profit < 0:
            return "High"
        elif delay > 0 or profit < 0:
            return "Medium"
        else:
            return "Low"

    df["Risk_Level"] = df.apply(calculate_risk, axis=1)

    # 4. Feature Selection
    feature_cols = [
        "Days for shipment (scheduled)",
        "Shipping Mode",
        "Customer Segment",
        "Category Name",
        "Product Price",
        "Sales",
        "Order Item Discount Rate"
    ]

    X = df[feature_cols].copy()
    y = df["Risk_Level"].copy()

    # Fill missing values
    X["Days for shipment (scheduled)"] = X["Days for shipment (scheduled)"].fillna(0).astype(int)
    X["Shipping Mode"] = X["Shipping Mode"].fillna("Standard Class").astype(str)
    X["Customer Segment"] = X["Customer Segment"].fillna("Consumer").astype(str)
    X["Category Name"] = X["Category Name"].fillna("Cleats").astype(str)
    X["Product Price"] = X["Product Price"].fillna(0.0).astype(float)
    X["Sales"] = X["Sales"].fillna(0.0).astype(float)
    X["Order Item Discount Rate"] = X["Order Item Discount Rate"].fillna(0.0).astype(float)

    # 5. Encode Categorical Features
    encoders = {}
    categorical_cols = ["Shipping Mode", "Customer Segment", "Category Name"]
    for col in categorical_cols:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col])
        encoders[col] = le

    # Encode target variable
    target_encoder = LabelEncoder()
    y_encoded = target_encoder.fit_transform(y)
    encoders["target"] = target_encoder
    classes = target_encoder.classes_.tolist()  # e.g. ['High', 'Low', 'Medium']

    # 6. Train / Test Split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    # 7. Train Decision Tree
    model = DecisionTreeClassifier(
        max_depth=8,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42
    )
    model.fit(X_train, y_train)

    # 8. Evaluate
    y_pred = model.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
    recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
    f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=classes, output_dict=True)

    logger.info(f"Accuracy={accuracy:.4f} | Precision={precision:.4f} | Recall={recall:.4f} | F1={f1:.4f}")

    # Confusion Matrix as structured dict
    cm_dict = {}
    for i, true_label in enumerate(classes):
        cm_dict[true_label] = {}
        for j, pred_label in enumerate(classes):
            cm_dict[true_label][pred_label] = int(cm[i][j])

    # Feature Importances
    importances = model.feature_importances_
    feature_importance_dict = dict(
        sorted(
            {col: float(imp) for col, imp in zip(feature_cols, importances)}.items(),
            key=lambda x: x[1],
            reverse=True
        )
    )

    # Per-class metrics
    per_class_metrics = {}
    for cls in classes:
        if cls in report:
            per_class_metrics[cls] = {
                "precision": round(report[cls]["precision"], 4),
                "recall": round(report[cls]["recall"], 4),
                "f1_score": round(report[cls]["f1-score"], 4),
                "support": int(report[cls]["support"])
            }

    # 9. Save Artifacts
    os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
    joblib.dump(model, Config.MODEL_PATH)
    joblib.dump(encoders, Config.ENCODER_PATH)

    metrics = {
        "accuracy": round(accuracy, 4),
        "precision_weighted": round(precision, 4),
        "recall_weighted": round(recall, 4),
        "f1_score_weighted": round(f1, 4),
        "confusion_matrix": cm_dict,
        "per_class_metrics": per_class_metrics,
        "feature_importance": feature_importance_dict,
        "classes": classes,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "model_params": {
            "max_depth": 8,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "class_weight": "balanced"
        }
    }

    metrics_path = os.path.join(os.path.dirname(Config.MODEL_PATH), "model_metrics.json")
    with open(metrics_path, "w") as mf:
        json.dump(metrics, mf, indent=4)

    logger.info(f"Model and metrics saved. Accuracy: {accuracy:.4f}")
    return metrics


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    train_model()
