"""
extract_features_json.py

Builds `ml_match_features.csv` directly from the JSON files in `ipl_json/`.
This is a fallback when a Postgres database is not available.

Usage: python extract_features_json.py
"""

from __future__ import annotations

import os
import json
from typing import Optional

import pandas as pd


JSON_DIR = os.path.join(os.path.dirname(__file__), "ipl_json")


def load_from_json(json_dir: str):
    matches_data = []
    deliveries_data = []

    for file in os.listdir(json_dir):
        if not file.endswith('.json'):
            continue
        match_id = file.split('.')[0]
        with open(os.path.join(json_dir, file), 'r', encoding='utf-8') as f:
            data = json.load(f)
            info = data.get('info', {})
            teams = info.get('teams', ['Unknown', 'Unknown'])
            toss = info.get('toss', {})
            outcome = data.get('info', {}).get('outcome', {})

            matches_data.append({
                'match_id': match_id,
                'season': info.get('season'),
                'date': info.get('dates', [None])[0],
                'venue': info.get('venue'),
                'team1': teams[0],
                'team2': teams[1],
                'toss_winner': toss.get('winner'),
                'toss_decision': toss.get('decision'),
                'winner': outcome.get('winner') if outcome else None,
            })

            innings = data.get('innings', [])
            for inning_idx, inning in enumerate(innings):
                team = inning.get('team')
                overs = inning.get('overs', [])
                for over in overs:
                    over_num = over.get('over')
                    for ball_num, delivery in enumerate(over.get('deliveries', []), start=1):
                        runs = delivery.get('runs', {})
                        wickets = delivery.get('wickets', [])
                        is_wicket = len(wickets) > 0
                        deliveries_data.append({
                            'match_id': match_id,
                            'inning': inning_idx + 1,
                            'batting_team': team,
                            'over': over_num,
                            'ball': ball_num,
                            'batter': delivery.get('batter'),
                            'bowler': delivery.get('bowler'),
                            'total_runs': runs.get('total', 0),
                            'is_wicket': is_wicket,
                        })

    df_matches = pd.DataFrame(matches_data)
    df_deliveries = pd.DataFrame(deliveries_data)
    df_matches['date'] = pd.to_datetime(df_matches['date'])
    return df_matches, df_deliveries


def compute_first_innings_totals(deliveries: pd.DataFrame) -> pd.DataFrame:
    fi = (
        deliveries[deliveries['inning'] == 1]
        .groupby('match_id', as_index=False)['total_runs']
        .sum()
        .rename(columns={'total_runs': 'first_innings_total'})
    )
    return fi


def team_recent_win_ratio(matches: pd.DataFrame, team: str, current_date: pd.Timestamp, window: int = 5) -> Optional[float]:
    played = matches[((matches['team1'] == team) | (matches['team2'] == team)) & (matches['date'] < current_date)]
    if played.shape[0] < window:
        return None
    recent = played.sort_values('date', ascending=False).head(window)
    wins = (recent['winner'] == team).sum()
    return float(wins) / float(window)


def venue_avg_first_innings_prior(matches_with_fi: pd.DataFrame, venue: str, current_date: pd.Timestamp) -> Optional[float]:
    venue_matches = matches_with_fi[(matches_with_fi['venue'] == venue) & (matches_with_fi['date'] < current_date)]
    if venue_matches.empty:
        return None
    return float(venue_matches['first_innings_total'].mean())


def head_to_head_win_ratio(matches: pd.DataFrame, team1: str, team2: str, current_date: pd.Timestamp) -> Optional[float]:
    """Calculate team1's historic win % specifically against team2 prior to current_date.
    
    Returns None if fewer than 1 prior head-to-head match exists.
    """
    h2h = matches[
        (((matches['team1'] == team1) & (matches['team2'] == team2)) | 
         ((matches['team1'] == team2) & (matches['team2'] == team1))) & 
        (matches['date'] < current_date)
    ]
    if h2h.shape[0] < 1:
        return None
    wins = (h2h['winner'] == team1).sum()
    return float(wins) / float(h2h.shape[0])


def venue_win_ratio(matches: pd.DataFrame, team: str, venue: str, current_date: pd.Timestamp) -> Optional[float]:
    """Calculate a team's win % at a specific venue prior to current_date.
    
    Returns None if the team has fewer than 1 prior match at this venue.
    """
    venue_matches = matches[
        ((matches['team1'] == team) | (matches['team2'] == team)) & 
        (matches['venue'] == venue) & 
        (matches['date'] < current_date)
    ]
    if venue_matches.shape[0] < 1:
        return None
    wins = (venue_matches['winner'] == team).sum()
    return float(wins) / float(venue_matches.shape[0])


def batting_strength_diff(matches: pd.DataFrame, deliveries: pd.DataFrame, team1: str, team2: str, current_date: pd.Timestamp, window: int = 5) -> Optional[float]:
    """Calculate the difference in average top-5 batter runs for team1 vs team2 in their last `window` matches.
    
    For each team's recent matches, find the top 5 batsmen by runs, compute mean runs,
    then return team1_avg - team2_avg. Returns None if insufficient data.
    """
    def get_recent_matches_for_team(team):
        return matches[
            ((matches['team1'] == team) | (matches['team2'] == team)) & 
            (matches['date'] < current_date)
        ].sort_values('date', ascending=False).head(window)
    
    def get_top_batters_avg_runs(team, match_ids_list):
        if not match_ids_list or len(match_ids_list) == 0:
            return None
        team_deliveries = deliveries[
            (deliveries['match_id'].isin(match_ids_list)) & 
            (deliveries['batting_team'] == team)
        ]
        if team_deliveries.empty:
            return None
        # Sum runs per batter across those matches
        batter_runs = team_deliveries.groupby('batter')['total_runs'].sum().sort_values(ascending=False)
        if len(batter_runs) < 5:
            return None
        top5_avg = float(batter_runs.head(5).mean())
        return top5_avg
    
    t1_recent = get_recent_matches_for_team(team1)
    t2_recent = get_recent_matches_for_team(team2)
    
    if t1_recent.shape[0] < window or t2_recent.shape[0] < window:
        return None
    
    t1_match_ids = list(t1_recent['match_id'].values)
    t2_match_ids = list(t2_recent['match_id'].values)
    
    t1_avg = get_top_batters_avg_runs(team1, t1_match_ids)
    t2_avg = get_top_batters_avg_runs(team2, t2_match_ids)
    
    if t1_avg is None or t2_avg is None:
        return None
    
    return t1_avg - t2_avg


def build_match_features(matches: pd.DataFrame, deliveries: pd.DataFrame) -> pd.DataFrame:
    fi_totals = compute_first_innings_totals(deliveries)
    matches_fi = matches.merge(fi_totals, on='match_id', how='left')
    matches_sorted = matches_fi.sort_values('date').reset_index(drop=True)

    rows = []
    for _, row in matches_sorted.iterrows():
        date = row['date']
        team1 = row['team1']
        team2 = row['team2']
        venue = row.get('venue')

        # Original features
        t1_ratio = team_recent_win_ratio(matches_sorted, team1, date, window=5)
        t2_ratio = team_recent_win_ratio(matches_sorted, team2, date, window=5)
        venue_avg = venue_avg_first_innings_prior(matches_sorted, venue, date)
        is_toss_winner_team1 = 1 if row.get('toss_winner') == team1 else 0
        
        # New complex features
        h2h_ratio = head_to_head_win_ratio(matches_sorted, team1, team2, date)
        venue_suit_t1 = venue_win_ratio(matches_sorted, team1, venue, date)
        venue_suit_t2 = venue_win_ratio(matches_sorted, team2, venue, date)
        bat_strength = batting_strength_diff(matches_sorted, deliveries, team1, team2, date, window=5)
        
        # Target
        if row.get('winner') == team1:
            target = 1
        elif row.get('winner') == team2:
            target = 0
        else:
            target = None

        rows.append({
            'match_id': row['match_id'],
            'season': row.get('season'),
            'date': date,
            'venue': venue,
            'team1': team1,
            'team2': team2,
            'team1_win_ratio_last_5': t1_ratio,
            'team2_win_ratio_last_5': t2_ratio,
            'venue_avg_first_innings': venue_avg,
            'is_toss_winner_team1': is_toss_winner_team1,
            'team1_head_to_head_win_ratio': h2h_ratio,
            'venue_suitability_team1': venue_suit_t1,
            'venue_suitability_team2': venue_suit_t2,
            'batting_strength_diff': bat_strength,
            'target_winner': target,
        })

    feat = pd.DataFrame(rows)
    feat_clean = feat.dropna().reset_index(drop=True)
    return feat_clean


def main():
    print(f"Loading JSON from {JSON_DIR}...")
    matches, deliveries = load_from_json(JSON_DIR)
    print(f"Parsed {len(matches)} matches and {len(deliveries)} deliveries")
    features = build_match_features(matches, deliveries)
    out_path = os.path.join(os.path.dirname(__file__), 'ml_match_features.csv')
    features.to_csv(out_path, index=False)
    print(f"Saved features to {out_path}. Rows: {len(features)}")


if __name__ == '__main__':
    main()
