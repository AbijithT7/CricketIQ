import os
import json
import pandas as pd
from sqlalchemy import create_engine

# 1. UPDATE THIS PATH to where your 1,243 json files are located
JSON_DIR = os.environ.get(
    "CRICIQ_JSON_DIR",
    r"C:\Users\abijith\Desktop\CricIQ\ipl_json",
)


def load_json_dataset(json_dir: str):
    matches_data = []
    deliveries_data = []

    for file in os.listdir(json_dir):
        if not file.endswith(".json"):
            continue

        match_id = file.split(".")[0]
        with open(os.path.join(json_dir, file), "r", encoding="utf-8") as f:
            data = json.load(f)
            info = data.get("info", {})
            teams = info.get("teams", ["Unknown", "Unknown"])
            toss = info.get("toss", {})
            outcome = data.get("outcome", {})

            matches_data.append(
                {
                    "match_id": match_id,
                    "season": info.get("season"),
                    "date": info.get("dates", [None])[0],
                    "city": info.get("city"),
                    "venue": info.get("venue"),
                    "team1": teams[0],
                    "team2": teams[1],
                    "toss_winner": toss.get("winner"),
                    "toss_decision": toss.get("decision"),
                    "winner": outcome.get("winner"),
                    "player_of_match": info.get("player_of_match", [None])[0]
                    if info.get("player_of_match")
                    else None,
                }
            )

            innings = data.get("innings", [])
            for inning_idx, inning in enumerate(innings):
                team = inning.get("team")
                overs = inning.get("overs", [])
                for over in overs:
                    over_num = over.get("over")
                    for ball_num, delivery in enumerate(over.get("deliveries", []), start=1):
                        wickets = delivery.get("wickets", [])
                        is_wicket = len(wickets) > 0
                        dismissal_kind = wickets[0].get("kind") if is_wicket else None
                        runs = delivery.get("runs", {})
                        deliveries_data.append(
                            {
                                "match_id": match_id,
                                "inning": inning_idx + 1,
                                "batting_team": team,
                                "over": over_num,
                                "ball": ball_num,
                                "batter": delivery.get("batter"),
                                "bowler": delivery.get("bowler"),
                                "non_striker": delivery.get("non_striker"),
                                "batter_runs": runs.get("batter", 0),
                                "extra_runs": runs.get("extras", 0),
                                "total_runs": runs.get("total", 0),
                                "is_wicket": is_wicket,
                                "dismissal_kind": dismissal_kind,
                            }
                        )

    df_matches = pd.DataFrame(matches_data)
    df_deliveries = pd.DataFrame(deliveries_data)
    return df_matches, df_deliveries


def build_engine():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres@localhost:5432/cricketiq"
    return create_engine(db_url)


def main():
    print("Parsing JSON files... this might take a minute.")
    df_matches, df_deliveries = load_json_dataset(JSON_DIR)
    print(f"Parsed {len(df_matches)} matches and {len(df_deliveries)} deliveries.")

    engine = build_engine()
    print("Uploading to PostgreSQL database...")
    df_matches.to_sql("matches", engine, if_exists="replace", index=False)
    df_deliveries.to_sql("deliveries", engine, if_exists="replace", index=False)
    print("Data successfully loaded into PostgreSQL!")


if __name__ == "__main__":
    main()
