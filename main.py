from __future__ import annotations

import os
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


MODEL_PATH = os.path.join(os.path.dirname(__file__), "xgb_match_predictor.pkl")

app = FastAPI(title="CricIQ Match Predictor API")

# Allow requests from local React dev server (include Vite dev server ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchPredictionRequest(BaseModel):
    team1_win_ratio_last_5: float
    team2_win_ratio_last_5: float
    venue_avg_first_innings: float
    is_toss_winner_team1: int
    team1_head_to_head_win_ratio: float
    venue_suitability_team1: float
    venue_suitability_team2: float
    batting_strength_diff: float
    toss_decision: Optional[str] = "bat"


model: Optional[object] = None
scaler: Optional[object] = None
features_df: Optional[pd.DataFrame] = None


@app.on_event("startup")
def load_model_on_startup():
    global model, scaler
    try:
        if os.path.exists(MODEL_PATH):
            loaded = joblib.load(MODEL_PATH)
            if isinstance(loaded, dict):
                model = loaded.get("model")
                scaler = loaded.get("scaler")
            else:
                model = loaded
                scaler = None
            print(f"Loaded model from {MODEL_PATH}")
        else:
            model = None
            scaler = None
            print(f"Model file not found at {MODEL_PATH}; starting without model.")
    except Exception as e:
        model = None
        scaler = None
        print(f"Failed to load model: {e}")

    # Load features CSV for lookups
    global features_df
    try:
        csv_path = os.path.join(os.path.dirname(__file__), "ml_match_features.csv")
        if os.path.exists(csv_path):
            features_df = pd.read_csv(csv_path)
            # normalize date and ensure string columns
            if "date" in features_df.columns:
                try:
                    features_df["date"] = pd.to_datetime(features_df["date"], errors="coerce")
                except Exception:
                    pass
            print(f"Loaded features CSV from {csv_path} ({len(features_df)} rows)")
        else:
            features_df = None
            print(f"Features CSV not found at {csv_path}")
    except Exception as e:
        features_df = None
        print(f"Failed to load features CSV: {e}")


def enrich_match_features(vals: dict, team1: str, team2: str, venue: str) -> dict:
    """Enriches basic features with score estimates and top player predictions."""
    venue_avg = vals.get("venue_avg_first_innings", 160.0)
    
    # 1. Expected first innings score (historical venue average)
    vals["expected_first_innings_score"] = round(venue_avg, 1)
    
    # 2. Powerplay score estimate (~35% of total)
    vals["powerplay_score"] = round(venue_avg * 0.35, 1)
    
    # 3. & 4. Top Run Scorer & Wicket Taker (Historical heuristics)
    venue_data = {
        "Wankhede Stadium": ("Rohit Sharma", "Jasprit Bumrah"),
        "Eden Gardens": ("Virat Kohli", "Sunil Narine"),
        "MA Chidambaram Stadium, Chepauk": ("MS Dhoni", "Ravindra Jadeja"),
        "M.Chinnaswamy Stadium": ("Virat Kohli", "Mohammed Siraj"),
        "Narendra Modi Stadium": ("Shubman Gill", "Rashid Khan"),
        "Arun Jaitley Stadium": ("Rishabh Pant", "Kuldeep Yadav"),
        "Rajiv Gandhi International Stadium": ("Heinrich Klaasen", "Pat Cummins"),
    }
    
    team_data = {
        "Chennai Super Kings": ("Ruturaj Gaikwad", "Matheesha Pathirana"),
        "Mumbai Indians": ("Suryakumar Yadav", "Jasprit Bumrah"),
        "Royal Challengers Bangalore": ("Virat Kohli", "Mohammed Siraj"),
        "Kolkata Knight Riders": ("Andre Russell", "Varun Chakaravarthy"),
        "Rajasthan Royals": ("Jos Buttler", "Yuzvendra Chahal"),
        "Gujarat Titans": ("Shubman Gill", "Rashid Khan"),
        "Lucknow Super Giants": ("KL Rahul", "Ravi Bishnoi"),
        "Delhi Capitals": ("Rishabh Pant", "Kuldeep Yadav"),
        "Sunrisers Hyderabad": ("Travis Head", "T Natarajan"),
        "Punjab Kings": ("Shashank Singh", "Arshdeep Singh"),
    }

    # Match venue first
    matched = False
    for v_key, (batter, bowler) in venue_data.items():
        if v_key.lower() in venue.lower():
            vals["top_run_scorer"] = batter
            vals["top_wicket_taker"] = bowler
            matched = True
            break
    
    if not matched:
        # Match team if venue fails
        if team1 in team_data:
            vals["top_run_scorer"], vals["top_wicket_taker"] = team_data[team1]
        elif team2 in team_data:
            vals["top_run_scorer"], vals["top_wicket_taker"] = team_data[team2]
        else:
            vals["top_run_scorer"] = "Virat Kohli"
            vals["top_wicket_taker"] = "Jasprit Bumrah"
            
    return vals


@app.get("/api/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}


@app.get("/api/features/{team1}/{team2}/{venue}")
def get_match_features(team1: str, team2: str, venue: str):
    """Return augmented features for the requested matchup."""
    if features_df is None:
        raise HTTPException(status_code=503, detail="Feature dataset not available on server.")

    df = features_df
    venue_mask = df["venue"].astype(str).str.contains(venue, case=False, na=False)
    team1_col = df["team1"].astype(str)
    team2_col = df["team2"].astype(str)

    # Handle historical team name aliases
    ALIASES = {
        "Delhi Capitals": ["Delhi Daredevils", "Delhi Capitals"],
        "Punjab Kings": ["Kings XI Punjab", "Punjab Kings"],
        "Sunrisers Hyderabad": ["Deccan Chargers", "Sunrisers Hyderabad"],
        "Rising Pune Supergiant": ["Pune Warriors", "Rising Pune Supergiants", "Rising Pune Supergiant"],
    }

    def get_variants(team_name):
        for main_name, variants in ALIASES.items():
            if team_name.lower() in [v.lower() for v in variants]:
                return variants
        return [team_name]

    t1_v = get_variants(team1)
    t2_v = get_variants(team2)

    mask_direct = (team1_col.str.lower().isin([v.lower() for v in t1_v])) & \
                  (team2_col.str.lower().isin([v.lower() for v in t2_v])) & \
                  venue_mask
    exact_rows = df[mask_direct]

    mask_swapped = (team1_col.str.lower().isin([v.lower() for v in t2_v])) & \
                   (team2_col.str.lower().isin([v.lower() for v in t1_v])) & \
                   venue_mask
    swapped_rows = df[mask_swapped]

    def get_row_values(rows):
        if rows is None or len(rows) == 0:
            return None
        # Use latest row
        row = rows.sort_values(by="date").iloc[-1] if "date" in rows.columns else rows.iloc[-1]
        return {
            "team1_win_ratio_last_5": float(row.get("team1_win_ratio_last_5", 0.0)),
            "team2_win_ratio_last_5": float(row.get("team2_win_ratio_last_5", 0.0)),
            "venue_avg_first_innings": float(row.get("venue_avg_first_innings", 0.0)),
            "team1_head_to_head_win_ratio": float(row.get("team1_head_to_head_win_ratio", 0.0)),
            "venue_suitability_team1": float(row.get("venue_suitability_team1", 0.0)),
            "venue_suitability_team2": float(row.get("venue_suitability_team2", 0.0)),
            "batting_strength_diff": float(row.get("batting_strength_diff", 0.0)),
        }

    # Case 1: Exact matchup
    vals = get_row_values(exact_rows)
    if vals:
        return enrich_match_features(vals, team1, team2, venue)

    # Case 2: Swapped matchup
    r = get_row_values(swapped_rows)
    if r:
        swapped_vals = {
            "team1_win_ratio_last_5": float(r["team2_win_ratio_last_5"]),
            "team2_win_ratio_last_5": float(r["team1_win_ratio_last_5"]),
            "venue_avg_first_innings": float(r["venue_avg_first_innings"]),
            "team1_head_to_head_win_ratio": 1.0 - float(r["team1_head_to_head_win_ratio"]),
            "venue_suitability_team1": float(r["venue_suitability_team2"]),
            "venue_suitability_team2": float(r["venue_suitability_team1"]),
            "batting_strength_diff": -float(r["batting_strength_diff"]),
        }
        return enrich_match_features(swapped_vals, team1, team2, venue)

    # Case 3: Fallback averages
    def get_avg_win_ratio(team_name):
        m1 = team1_col.str.lower() == team_name.lower()
        m2 = team2_col.str.lower() == team_name.lower()
        v1 = df.loc[m1, "team1_win_ratio_last_5"] if m1.any() else pd.Series(dtype=float)
        v2 = df.loc[m2, "team2_win_ratio_last_5"] if m2.any() else pd.Series(dtype=float)
        all_v = pd.concat([v1, v2])
        return float(all_v.mean()) if not all_v.empty else 0.5

    venue_vals = df.loc[venue_mask, "venue_avg_first_innings"] if venue_mask.any() else pd.Series(dtype=float)
    venue_avg = float(venue_vals.mean()) if not venue_vals.empty else 160.0

    mask_either = ((team1_col.str.lower() == team1.lower()) & (team2_col.str.lower() == team2.lower())) | \
                  ((team1_col.str.lower() == team2.lower()) & (team2_col.str.lower() == team1.lower()))
    h2h_rows = df[mask_either]
    h2h_list = []
    for _, row in h2h_rows.iterrows():
        val = float(row.get("team1_head_to_head_win_ratio", 0.5))
        h2h_list.append(val if str(row["team1"]).lower() == team1.lower() else 1.0 - val)
    h2h_avg = float(pd.Series(h2h_list).mean()) if h2h_list else 0.5

    vs_t1_vals = []
    vs_t2_vals = []
    for _, r in df[venue_mask].iterrows():
        if str(r["team1"]).lower() == team1.lower(): vs_t1_vals.append(float(r.get("venue_suitability_team1", 0.5)))
        if str(r["team2"]).lower() == team1.lower(): vs_t1_vals.append(float(r.get("venue_suitability_team2", 0.5)))
        if str(r["team1"]).lower() == team2.lower(): vs_t2_vals.append(float(r.get("venue_suitability_team1", 0.5)))
        if str(r["team2"]).lower() == team2.lower(): vs_t2_vals.append(float(r.get("venue_suitability_team2", 0.5)))

    bsd_list = []
    for _, r in h2h_rows.iterrows():
        val = float(r.get("batting_strength_diff", 0.0))
        bsd_list.append(val if str(r["team1"]).lower() == team1.lower() else -val)

    fallback_vals = {
        "team1_win_ratio_last_5": get_avg_win_ratio(team1),
        "team2_win_ratio_last_5": get_avg_win_ratio(team2),
        "venue_avg_first_innings": venue_avg,
        "team1_head_to_head_win_ratio": h2h_avg,
        "venue_suitability_team1": float(pd.Series(vs_t1_vals).mean()) if vs_t1_vals else 0.5,
        "venue_suitability_team2": float(pd.Series(vs_t2_vals).mean()) if vs_t2_vals else 0.5,
        "batting_strength_diff": float(pd.Series(bsd_list).mean()) if bsd_list else 0.0,
    }
    return enrich_match_features(fallback_vals, team1, team2, venue)


@app.post("/api/predict/match")
def predict_match(payload: MatchPredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not available.")

    feature_order = [
        "team1_win_ratio_last_5", "team2_win_ratio_last_5", "venue_avg_first_innings",
        "is_toss_winner_team1", "team1_head_to_head_win_ratio", "venue_suitability_team1",
        "venue_suitability_team2", "batting_strength_diff"
    ]
    
    X = pd.DataFrame([payload.dict()])[feature_order]

    try:
        if scaler is not None:
            X = scaler.transform(X)
        preds = model.predict(X)
        probs = model.predict_proba(X)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return {"predicted_label": int(preds[0]), "probabilities": [float(p) for p in probs[0]]}
