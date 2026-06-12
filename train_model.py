"""
train_model.py

Train an XGBoost classifier on `ml_match_features.csv` and save model.

Usage: python train_model.py

Dependencies: pandas, scikit-learn, xgboost, joblib
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


FEATURE_COLUMNS = [
    "team1_win_ratio_last_5",
    "team2_win_ratio_last_5",
    "venue_avg_first_innings",
    "is_toss_winner_team1",
    "team1_head_to_head_win_ratio",
    "venue_suitability_team1",
    "venue_suitability_team2",
    "batting_strength_diff",
]


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def chronological_train_test_split(df: pd.DataFrame, train_frac: float = 0.8):
    if "date" in df.columns:
        df_sorted = df.sort_values("date").reset_index(drop=True)
    else:
        df_sorted = df.sort_index().reset_index(drop=True)
    n_train = int(len(df_sorted) * train_frac)
    train = df_sorted.iloc[:n_train]
    test = df_sorted.iloc[n_train:]
    return train, test


def train_and_evaluate(df: pd.DataFrame) -> None:
    train, test = chronological_train_test_split(df, train_frac=0.8)

    X_train = train[FEATURE_COLUMNS]
    y_train = train["target_winner"]
    X_test = test[FEATURE_COLUMNS]
    y_test = test["target_winner"]

    # Scale features for better model performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Tuned XGBoost hyperparameters
    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42
    )
    model.fit(X_train_scaled, y_train)

    preds = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, preds)
    print(f"Test Accuracy: {acc:.4f}")
    print("Classification Report:")
    print(classification_report(y_test, preds))

    # Save model and scaler together
    out_path = Path("xgb_match_predictor.pkl")
    joblib.dump({"model": model, "scaler": scaler}, out_path)
    print(f"Saved trained model and scaler to {out_path}")


def main():
    csv_path = Path("ml_match_features.csv")
    if not csv_path.exists():
        print(f"Error: {csv_path} not found. Run extract_features.py first.")
        sys.exit(1)

    try:
        df = load_data(csv_path)
    except Exception as e:
        print(f"Failed to load CSV: {e}")
        sys.exit(1)

    # Check required columns
    missing = [c for c in FEATURE_COLUMNS + ["target_winner"] if c not in df.columns]
    if missing:
        print(f"CSV is missing required columns: {missing}")
        sys.exit(1)

    # Drop rows with NaNs in features/target
    df_clean = df.dropna(subset=FEATURE_COLUMNS + ["target_winner"]).reset_index(drop=True)

    if df_clean.empty:
        print("No data available after dropping NaNs. Exiting.")
        sys.exit(1)

    train_and_evaluate(df_clean)


if __name__ == "__main__":
    main()
