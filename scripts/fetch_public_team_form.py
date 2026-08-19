"""Collect public recent-results samples without depending on a paid football API."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fetch_match_radar_enrichment import SPORTSCORE_TEAM_SLUGS, TEAM_ALIASES, sportscore_team

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def normalise(team: str, payload: dict) -> list[dict]:
    rows = []
    for match in payload.get("matches", []):
        if match.get("status") != "finished":
            continue
        try:
            home_score, away_score = int(match.get("home_score")), int(match.get("away_score"))
        except (TypeError, ValueError):
            continue
        is_home = str(match.get("home", "")).casefold() == team.casefold()
        is_away = str(match.get("away", "")).casefold() == team.casefold()
        if not (is_home or is_away):
            continue
        gf, ga = (home_score, away_score) if is_home else (away_score, home_score)
        rows.append({
            "date": str(match.get("time") or "")[:10], "venue": "home" if is_home else "away",
            "opponent": match.get("away") if is_home else match.get("home"), "gf": gf, "ga": ga,
            "result": "W" if gf > ga else "D" if gf == ga else "L", "competition": match.get("competition"),
        })
    return sorted(rows, key=lambda row: row["date"], reverse=True)[:5]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    source = json.loads((DATA / f"sporttery_{args.date}_latest.json").read_text(encoding="utf-8-sig"))
    cache: dict[str, list[dict]] = {}
    output = {"version": "sportscore-public-form-v1", "source": "https://sportscore.com/developers/", "matches": {}}
    for match in source.get("matches", []):
        aliases = TEAM_ALIASES.get((str(match.get("homeCode")), str(match.get("awayCode"))))
        if not aliases:
            continue
        sides = {}
        for side, team in zip(("home", "away"), aliases):
            if team not in cache:
                try:
                    raw = sportscore_team(SPORTSCORE_TEAM_SLUGS[team])
                    cache[team] = normalise((raw.get("team") or {}).get("name") or team, raw)
                except Exception:
                    cache[team] = []
            sides[side] = cache[team]
        output["matches"][str(match.get("matchId") or match.get("id"))] = sides
    path = DATA / f"public_team_form_{args.date}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"matches": len(output["matches"]), "teamsWithForm": sum(bool(x) for x in cache.values()), "output": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
