"""
extract_features.py

Connects to local Postgres `cricketiq` DB and builds match-level features
for ML. Saves output to `ml_match_features.csv`.

Requirements: pandas, sqlalchemy, psycopg2

Features computed per match:
- team1_win_ratio_last_5: proportion (0-1) of wins in last 5 matches prior to this match
- team2_win_ratio_last_5: same for team2
- venue_avg_first_innings: average first-innings total at this venue prior to this match
- is_toss_winner_team1: 1 if team1 won toss else 0
- target_winner: 1 if team1 won the match, 0 if team2 won, NaN otherwise

Rows with NaN (due to insufficient history) are dropped before saving.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine


def get_db_engine() -> 'Engine':
    """Create SQLAlchemy engine for local postgres `cricketiq` database.

    Assumes a local Postgres instance reachable at port 5432 and a user
    named `postgres` with no password configured for localhost access. If
    your setup differs, set the `DATABASE_URL` environment variable to a
    valid SQLAlchemy DSN (for example:
    postgresql://user:password@localhost:5432/cricketiq).
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Default local connection (no password). Adjust env var to override.
        db_url = "postgresql://postgres@localhost:5432/cricketiq"
    return create_engine(db_url)


def load_tables(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load `matches` and `deliveries` tables into DataFrames."""
    matches = pd.read_sql_query("SELECT * FROM matches", engine)
    deliveries = pd.read_sql_query("SELECT * FROM deliveries", engine)

    # Ensure dates are parsed
    matches["date"] = pd.to_datetime(matches["date"])
    return matches, deliveries


def compute_first_innings_totals(deliveries: pd.DataFrame) -> pd.DataFrame:
    """Compute first-innings total runs per match.

    Returns DataFrame with columns `match_id` and `first_innings_total`.
    """
    fi = (
        deliveries[deliveries["inning"] == 1]
        .groupby("match_id", as_index=False)["total_runs"]
        .sum()
        .rename(columns={"total_runs": "first_innings_total"})
    )
    return fi


def team_recent_win_ratio(
    matches: pd.DataFrame, team: str, current_date: pd.Timestamp, window: int = 5
) -> Optional[float]:
    """Calculate the win ratio (0-1) for `team` in their last `window`
    matches strictly before `current_date`.

    If fewer than `window` prior matches exist, return None. This enforces
    a fixed-size rolling window and allows dropping early matches with
    insufficient history.
    """
    # Filter matches where the team played and which are before current_date
    played = matches[
        ((matches["team1"] == team) | (matches["team2"] == team))
        & (matches["date"] < current_date)
    ]
    if played.shape[0] < window:
        return None
    # Take the most recent `window` matches
    recent = played.sort_values("date", ascending=False).head(window)
    wins = (recent["winner"] == team).sum()
    return float(wins) / float(window)


def venue_avg_first_innings_prior(
    matches_with_fi: pd.DataFrame, venue: str, current_date: pd.Timestamp
) -> Optional[float]:
    """Compute the mean of first-innings totals at `venue` for matches
    strictly before `current_date`. If no prior matches, return None.
    """
    venue_matches = (
        matches_with_fi[(matches_with_fi["venue"] == venue) & (matches_with_fi["date"] < current_date)]
    )
    if venue_matches.empty:
        return None
    return float(venue_matches["first_innings_total"].mean())


def build_match_features(matches: pd.DataFrame, deliveries: pd.DataFrame) -> pd.DataFrame:
    """Construct `match_features` DataFrame with required aggregated features.

    This is intentionally simple and iterative: for each match we compute
    historical (date < current match date) statistics for both teams and
    the venue. The logic enforces strict "prior to match" windows so that
    no future information leaks into features.
    """
    # Prepare first-innings totals and join into matches
    fi_totals = compute_first_innings_totals(deliveries)
    matches_fi = matches.merge(fi_totals, on="match_id", how="left")

    # Sort matches by date to make iteration deterministic
    matches_sorted = matches_fi.sort_values("date").reset_index(drop=True)

    rows = []
    for _, row in matches_sorted.iterrows():
        mid = row["match_id"]
        date = row["date"]
        team1 = row["team1"]
        team2 = row["team2"]
        venue = row.get("venue")

        # team win ratios in last 5 matches prior to this match (0-1). If
        # fewer than 5 prior matches exist, we return None which will
        # become NaN in the DataFrame and be dropped later.
        t1_ratio = team_recent_win_ratio(matches_sorted, team1, date, window=5)
        t2_ratio = team_recent_win_ratio(matches_sorted, team2, date, window=5)

        # venue average of first innings prior to this match
        venue_avg = venue_avg_first_innings_prior(matches_sorted, venue, date)

        is_toss_winner_team1 = 1 if row.get("toss_winner") == team1 else 0

        # target: 1 if team1 won, 0 if team2 won, else None (e.g., no result)
        if row.get("winner") == team1:
            target = 1
        elif row.get("winner") == team2:
            target = 0
        else:
            target = None

        rows.append(
            {
                "match_id": mid,
                "season": row.get("season"),
                "date": date,
                "venue": venue,
                "team1": team1,
                "team2": team2,
                "team1_win_ratio_last_5": t1_ratio,
                "team2_win_ratio_last_5": t2_ratio,
                "venue_avg_first_innings": venue_avg,
                "is_toss_winner_team1": is_toss_winner_team1,
                "target_winner": target,
            }
        )

    feat = pd.DataFrame(rows)

    # Drop rows with any NaN/None values (these come from insufficient
    # historical data or missing winners). This enforces that all examples
    # have full history available.
    feat_clean = feat.dropna().reset_index(drop=True)
    return feat_clean


def main() -> None:
    engine = get_db_engine()
    print("Connecting to database and loading tables...")
    matches, deliveries = load_tables(engine)

    print("Building match-level features (this may take a while)...")
    match_features = build_match_features(matches, deliveries)

    out_path = "ml_match_features.csv"
    match_features.to_csv(out_path, index=False)
    print(f"Saved features to {out_path}. Rows: {len(match_features)}")


if __name__ == "__main__":
    main()
