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

            players_info = info.get('players', {})
            team1_players = players_info.get(teams[0], [])
            team2_players = players_info.get(teams[1], [])

            innings = data.get('innings', [])
            team_batting_second = None
            if len(innings) > 1:
                team_batting_second = innings[1].get('team')
            else:
                toss_winner = toss.get('winner')
                toss_decision = toss.get('decision')
                if toss_winner and toss_decision:
                    if toss_decision == 'field':
                        team_batting_second = toss_winner
                    else:
                        team_batting_second = teams[1] if teams[0] == toss_winner else teams[0]

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
                'team_batting_second': team_batting_second,
                'team1_players': team1_players,
                'team2_players': team2_players,
            })

            for inning_idx, inning in enumerate(innings):
                team = inning.get('team')
                overs = inning.get('overs', [])
                for over in overs:
                    over_num = over.get('over')
                    for ball_num, delivery in enumerate(over.get('deliveries', []), start=1):
                        runs = delivery.get('runs', {})
                        extras = delivery.get('extras', {})
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
                            'batter_runs': runs.get('batter', 0),
                            'wide_runs': extras.get('wides', 0),
                            'noball_runs': extras.get('noballs', 0),
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

    # Precompute player match-level stats
    # batting stats per player per match
    deliveries['ball_faced'] = (deliveries['wide_runs'] == 0).astype(int)
    batting_stats = deliveries.groupby(['match_id', 'batter'], as_index=False).agg(
        runs_scored=('batter_runs', 'sum'),
        balls_faced=('ball_faced', 'sum')
    ).rename(columns={'batter': 'player'})

    # bowling stats per player per match
    deliveries['runs_conceded_bowler'] = deliveries['batter_runs'] + deliveries['wide_runs'] + deliveries['noball_runs']
    deliveries['legal_ball'] = ((deliveries['wide_runs'] == 0) & (deliveries['noball_runs'] == 0)).astype(int)
    bowling_stats = deliveries.groupby(['match_id', 'bowler'], as_index=False).agg(
        runs_conceded=('runs_conceded_bowler', 'sum'),
        legal_balls_bowled=('legal_ball', 'sum')
    ).rename(columns={'bowler': 'player'})

    # Merge player match stats
    player_match_df = pd.merge(batting_stats, bowling_stats, on=['match_id', 'player'], how='outer').fillna(0)
    # Group by match_id for fast lookup
    player_stats_by_match = {match_id: grp for match_id, grp in player_match_df.groupby('match_id')}

    player_career = {}

    # Sort matches by date to ensure chronological order
    matches_sorted = matches_fi.sort_values('date').reset_index(drop=True)

    rows = []
    # Group matches by date to handle doubleheaders without leaking stats from the same day
    grouped_by_date = matches_sorted.groupby('date')
    dates = sorted(grouped_by_date.groups.keys())

    for dt in dates:
        date_matches = grouped_by_date.get_group(dt)
        for _, row in date_matches.iterrows():
            match_id = row['match_id']
            team1 = row['team1']
            team2 = row['team2']
            venue = row.get('venue')
            t1_players = row.get('team1_players', [])
            t2_players = row.get('team2_players', [])

            # 1. Compute venue_chase_bias prior to dt
            venue_matches = matches_sorted[
                (matches_sorted['venue'] == venue) & 
                (matches_sorted['date'] < dt) & 
                (matches_sorted['winner'].notna())
            ]
            if venue_matches.shape[0] < 1:
                venue_chase = None
            else:
                chase_wins = (venue_matches['winner'] == venue_matches['team_batting_second']).sum()
                venue_chase = float(chase_wins) / float(venue_matches.shape[0])

            # 2. Count star players in team1 and team2 lineups using player_career prior to dt
            # Batter star criteria: strike rate > 135 (with min 10 balls faced to filter noise)
            # Bowler star criteria: economy < 7.5 (with min 12 legal balls bowled to filter noise)
            def count_star_players(player_list):
                star_count = 0
                for p in player_list:
                    stats = player_career.get(p, {'runs_scored': 0, 'balls_faced': 0, 'runs_conceded': 0, 'legal_balls_bowled': 0})
                    is_star = False
                    
                    if stats['balls_faced'] >= 10:
                        sr = (float(stats['runs_scored']) / stats['balls_faced']) * 100.0
                        if sr > 135.0:
                            is_star = True
                            
                    if stats['legal_balls_bowled'] >= 12:
                        econ = (float(stats['runs_conceded']) / stats['legal_balls_bowled']) * 6.0
                        if econ < 7.5:
                            is_star = True
                            
                    if is_star:
                        star_count += 1
                return star_count

            t1_star = count_star_players(t1_players)
            t2_star = count_star_players(t2_players)

            # Original features
            t1_ratio = team_recent_win_ratio(matches_sorted, team1, dt, window=5)
            t2_ratio = team_recent_win_ratio(matches_sorted, team2, dt, window=5)
            venue_avg = venue_avg_first_innings_prior(matches_sorted, venue, dt)
            is_toss_winner_team1 = 1 if row.get('toss_winner') == team1 else 0
            
            # New complex features
            h2h_ratio = head_to_head_win_ratio(matches_sorted, team1, team2, dt)
            venue_suit_t1 = venue_win_ratio(matches_sorted, team1, venue, dt)
            venue_suit_t2 = venue_win_ratio(matches_sorted, team2, venue, dt)
            bat_strength = batting_strength_diff(matches_sorted, deliveries, team1, team2, dt, window=5)
            
            # Target
            if row.get('winner') == team1:
                target = 1
            elif row.get('winner') == team2:
                target = 0
            else:
                target = None

            rows.append({
                'match_id': match_id,
                'season': row.get('season'),
                'date': dt,
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
                'venue_chase_bias': venue_chase,
                'team1_star_players': t1_star,
                'team2_star_players': t2_star,
                'target_winner': target,
            })

        # Update player_career with stats from matches played on this date (only after processing all of them)
        for _, row in date_matches.iterrows():
            match_id = row['match_id']
            if match_id in player_stats_by_match:
                match_stats = player_stats_by_match[match_id]
                for _, p_row in match_stats.iterrows():
                    p = p_row['player']
                    if p not in player_career:
                        player_career[p] = {'runs_scored': 0, 'balls_faced': 0, 'runs_conceded': 0, 'legal_balls_bowled': 0}
                    player_career[p]['runs_scored'] += p_row['runs_scored']
                    player_career[p]['balls_faced'] += p_row['balls_faced']
                    player_career[p]['runs_conceded'] += p_row['runs_conceded']
                    player_career[p]['legal_balls_bowled'] += p_row['legal_balls_bowled']

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
