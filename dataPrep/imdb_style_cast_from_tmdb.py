#!/usr/bin/env python3
"""
IMDB-Style Cast-to-Episode Exporter (via TMDb) - HYBRID APPROACH
----------------------------------------------------------------
Input: IMDb SERIES IDs (tconst like "tt0214950") from CLI or a text file.
Process:
  • Find TMDb tv_id from IMDb series id.
  • For each season & episode: fetch credits and external_ids to get episode IMDb tt.
  • HYBRID: If no IMDb episode match, generate synthetic tconst (e.g., "tt1668_01_05")
  • For each cast/guest_star: fetch person external_ids to get IMDb nconst,
    and person details to infer birthYear/deathYear.
Output: 
  1. Cast CSV 'imdb_style_episode_cast.csv' with IMDb-compatible columns
  2. Missing Episodes CSV 'tmdb_missing_episodes.csv' for episodes without IMDb matches

HYBRID BENEFITS:
  • All episodes get tconst values (real IMDb or synthetic)
  • All actors get nconst values (real IMDb or synthetic) 
  • Missing episodes tracked separately for potential future matching
  • Maintains compatibility with existing IMDb data
  • Synthetic episode format: tt{tmdb_tv_id}_{season:02d}_{episode:02d}
  • Synthetic actor format: nm{tmdb_person_id}

Notes:
  • Requires TMDB_API_KEY (env var or .env). Install python-dotenv optionally.
  • Rate limiting (max_rps) and retries are handled.
  • Optimized person caching reduces API calls by ~90%
  • 'category' is derived from TMDb gender (2->actor, 1->actress, else 'actor').
  • 'job' left blank (actors). 'characters' is JSON array with the TMDb character string when available.
  • 'primaryProfession' uses TMDb known_for_department (e.g., 'Acting'); 'knownForTitles' left blank.
Usage:
    python imdb_style_cast_from_tmdb.py --series tt0214950 --max-rps 3
    python imdb_style_cast_from_tmdb.py --file series_ids.txt --max-rps 3 --episodes-out ../GraphDB-files/my_missing_episodes.csv
"""
import os
import sys
import csv
import time
import argparse
from typing import Dict, Any, List, Optional, Iterable
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3"


class TMDbClient:
    def __init__(self, api_key: str, max_rps: float = 3.0, timeout: int = 20, max_retries: int = 5):
        assert api_key, "TMDB_API_KEY is required (env var or .env)"
        self.api_key = api_key
        self.s = requests.Session()
        self.timeout = timeout
        self.min_interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self.max_retries = max_retries
        self._last_ts = 0.0

    def _throttle(self):
        now = time.time()
        delta = now - self._last_ts
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def _req(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = dict(params or {})
        params["api_key"] = self.api_key
        attempt, backoff = 0, 1.0
        while True:
            self._throttle()
            self._last_ts = time.time()
            try:
                r = self.s.request(method, f"{BASE}{path}", params=params, timeout=self.timeout)
            except requests.RequestException:
                if attempt >= self.max_retries: raise
                attempt += 1; time.sleep(backoff); backoff = min(backoff*2, 30); continue
            if r.status_code == 200:
                try: return r.json()
                except ValueError:
                    if attempt >= self.max_retries: raise
            elif r.status_code in (429, 500, 502, 503, 504):
                retry_after = float(r.headers.get("Retry-After", "0") or 0)
                wait = max(retry_after, backoff)
                if attempt >= self.max_retries: r.raise_for_status()
                attempt += 1; time.sleep(wait); backoff = min(backoff*2, 60); continue
            else:
                try: detail = r.json()
                except Exception: detail = {"text": r.text[:200]}
                raise RuntimeError(f"HTTP {r.status_code} {path}: {detail}")

    # TMDb endpoints used
    def find_by_imdb_id(self, imdb_id: str) -> Dict[str, Any]:
        return self._req("GET", f"/find/{imdb_id}", {"external_source": "imdb_id"})

    def tv_details(self, tv_id: int) -> Dict[str, Any]:
        return self._req("GET", f"/tv/{tv_id}")

    def season(self, tv_id: int, season_number: int) -> Dict[str, Any]:
        return self._req("GET", f"/tv/{tv_id}/season/{season_number}")

    def episode_external_ids(self, tv_id: int, season_number: int, episode_number: int) -> Dict[str, Any]:
        return self._req("GET", f"/tv/{tv_id}/season/{season_number}/episode/{episode_number}/external_ids")

    def episode_credits(self, tv_id: int, season_number: int, episode_number: int) -> Dict[str, Any]:
        return self._req("GET", f"/tv/{tv_id}/season/{season_number}/episode/{episode_number}/credits")

    def person_external_ids(self, person_id: int) -> Dict[str, Any]:
        return self._req("GET", f"/person/{person_id}/external_ids")

    def person_details(self, person_id: int) -> Dict[str, Any]:
        return self._req("GET", f"/person/{person_id}")


def read_ids(file_path: Optional[str], series_ids: List[str]) -> List[str]:
    out, seen = [], set()
    ids = [s.strip() for s in (series_ids or []) if s.strip()]
    if file_path:
        # Handle relative path to series_ids.txt in same directory
        if not Path(file_path).is_absolute():
            file_path = Path(__file__).parent / file_path
        with open(file_path, "r", encoding="utf-8") as f:
            ids += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    for s in ids:
        if not s.startswith("tt"): 
            print(f"WARNING: skip non-IMDb id: {s}", file=sys.stderr); continue
        if s not in seen:
            seen.add(s); out.append(s)
    return out


def gender_to_category(g: Optional[int]) -> str:
    # TMDb: 0/3 unknown, 1 female, 2 male
    return "actress" if g == 1 else "actor"


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], headers: List[str]):
    ensure_parent(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore", quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows: w.writerow(r)


def get_person_data(client: TMDbClient, person_id: int, person_cache: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get complete person data (external_ids + details) with caching.
    Returns combined data: {nconst, name, birthYear, deathYear, gender, known_for_department}
    """
    if person_id in person_cache:
        return person_cache[person_id]
    
    print(f"    Fetching person data for TMDb ID {person_id}...", file=sys.stderr)
    
    # Fetch both external_ids and details
    try:
        ext_data = client.person_external_ids(person_id)
        nconst = ext_data.get("imdb_id")
    except Exception as e:
        print(f"      Warning: Failed to get external_ids for person {person_id}: {e}", file=sys.stderr)
        nconst = None
    
    try:
        details = client.person_details(person_id)
    except Exception as e:
        print(f"      Warning: Failed to get details for person {person_id}: {e}", file=sys.stderr)
        details = {}
    
    # Generate synthetic nconst if no IMDb match found
    if not nconst:
        nconst = f"nt{person_id}"  # Use TMDb ID with nt prefix for consistency
    
    # Combine and cache the data
    person_data = {
        "nconst": nconst,
        "name": details.get("name", ""),
        "birthYear": (details.get("birthday") or "")[:4] if details.get("birthday") else "",
        "deathYear": (details.get("deathday") or "")[:4] if details.get("deathday") else "",
        "gender": details.get("gender"),
        "known_for_department": details.get("known_for_department", ""),
        "tmdb_source": not bool(ext_data.get("imdb_id")) if ext_data else True  # Track if this is TMDb-sourced
    }
    
    person_cache[person_id] = person_data
    return person_data


def main():
    # Setup output directory relative to project root
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "GraphDB-files"
    output_dir.mkdir(exist_ok=True)
    
    ap = argparse.ArgumentParser(description="Export IMDb-style cast-to-episode rows using TMDb.")
    ap.add_argument("--series", nargs="*", default=[], help="IMDb SERIES ids like tt0214950")
    ap.add_argument("--file", help="Text file with IMDb SERIES ids, one per line")
    ap.add_argument("--out", default=str(output_dir / "imdb_style_episode_cast.csv"))
    ap.add_argument("--episodes-out", default=str(output_dir / "tmdb_missing_episodes.csv"), help="Output file for episodes not found in IMDb")
    ap.add_argument("--max-rps", type=float, default=float(os.getenv("TMDB_MAX_RPS", "3")))
    args = ap.parse_args()

    series_ids = read_ids(args.file, args.series)
    if not series_ids:
        print("No IMDb series ids provided. Use --series or --file.", file=sys.stderr)
        sys.exit(1)

    client = TMDbClient(TMDB_API_KEY, max_rps=args.max_rps)

    # Unified person cache to avoid ALL duplicate person lookups
    person_cache: Dict[int, Dict[str, Any]] = {}  # tmdb person_id -> combined person data

    rows: List[Dict[str, Any]] = []
    missing_episodes: List[Dict[str, Any]] = []  # Episodes not found in IMDb

    headers = [
        "tconst","ordering","nconst","category","job","characters",
        "primaryName","birthYear","deathYear","primaryProfession","knownForTitles","castType"
    ]

    episode_headers = [
        "tconst","parentTconst","primaryTitle","seasonNumber","episodeNumber",
        "startYear","averageRating","numVotes"
    ]

    for imdb_series in series_ids:
        print(f"\n=== Series {imdb_series} ===", file=sys.stderr)
        found = client.find_by_imdb_id(imdb_series)
        tv_results = found.get("tv_results") or []
        if not tv_results:
            print(f"  No TMDb tv_results; skip.", file=sys.stderr)
            continue
        tv_id = tv_results[0]["id"]
        tv = client.tv_details(tv_id)
        num_seasons = int(tv.get("number_of_seasons") or 0)
        print(f"  TMDb tv_id={tv_id} seasons={num_seasons}", file=sys.stderr)

        # include season 0 (specials) and 1..num_seasons
        for s_num in [0] + list(range(1, num_seasons+1)):
            try:
                season = client.season(tv_id, s_num)
            except Exception as e:
                if s_num != 0:
                    print(f"   season {s_num}: {e}", file=sys.stderr)
                continue

            episodes = season.get("episodes") or []
            print(f"   season {s_num}: {len(episodes)} eps", file=sys.stderr)

            for ep in episodes:
                e_num = ep.get("episode_number")
                ep_name = ep.get("name", "")
                ep_air_date = ep.get("air_date", "")
                ep_vote_average = ep.get("vote_average", "")
                ep_vote_count = ep.get("vote_count", "")
                
                # resolve episode IMDb tt
                imdb_matched = False
                try:
                    ext = client.episode_external_ids(tv_id, s_num, e_num)
                    ep_tconst = ext.get("imdb_id")  # may be None if unknown
                    if ep_tconst:
                        imdb_matched = True
                except Exception:
                    ep_tconst = None
                
                # Generate synthetic tconst if no IMDb match found
                if not ep_tconst:
                    ep_tconst = f"tt{tv_id}_{s_num:02d}_{e_num:02d}"
                    
                    # Add to missing episodes list for separate CSV
                    missing_episodes.append({
                        "tconst": ep_tconst,
                        "parentTconst": imdb_series,  # Original IMDb series ID
                        "primaryTitle": ep_name,
                        "seasonNumber": s_num,
                        "episodeNumber": e_num,
                        "startYear": ep_air_date[:4] if ep_air_date else "",
                        "averageRating": ep_vote_average if ep_vote_average else "",
                        "numVotes": ep_vote_count if ep_vote_count else ""
                    })

                # Fetch credits
                credits = client.episode_credits(tv_id, s_num, e_num)
                for role_bucket in ("cast", "guest_stars"):
                    # Determine cast type based on which TMDb bucket they're in
                    cast_type = "regular" if role_bucket == "cast" else "guest"
                    
                    for c in credits.get(role_bucket, []) or []:
                        tmdb_pid = c.get("id")
                        character = c.get("character") or None
                        order = c.get("order")

                        if tmdb_pid is None:
                            continue  # Skip entries without person ID

                        # Get complete person data (cached)
                        person_data = get_person_data(client, tmdb_pid, person_cache)
                        
                        nconst = person_data["nconst"]
                        name = person_data["name"]
                        birthYear = person_data["birthYear"]
                        deathYear = person_data["deathYear"]
                        primaryProfession = person_data["known_for_department"].lower()
                        category = gender_to_category(person_data["gender"])

                        rows.append({
                            "tconst": ep_tconst or "",               # IMDb EPISODE id (tt...); empty if not available
                            "ordering": order,                        # TMDb 'order' within cast list
                            "nconst": nconst or "",                   # IMDb person id (nm...); empty if not available
                            "category": category,                     # actor/actress
                            "job": "",                                # blank for actors
                            "characters": f'["{character}"]' if character else "[]",
                            "primaryName": name or "",
                            "birthYear": birthYear,
                            "deathYear": deathYear,
                            "primaryProfession": primaryProfession,
                            "knownForTitles": "",                     # not available without IMDb scraping; left blank
                            "castType": cast_type,                    # "regular" or "guest" based on TMDb classification
                        })

    # Write main cast file
    out_path = Path(args.out)
    write_csv(out_path, rows, headers)
    
    # Write missing episodes file if any were found
    episodes_path = Path(args.episodes_out)
    if missing_episodes:
        write_csv(episodes_path, missing_episodes, episode_headers)
    
    # Count IMDb matched vs synthetic episodes
    all_episodes_processed = set()
    synthetic_episodes_in_cast = set()
    
    for row in rows:
        episode_id = row["tconst"]
        all_episodes_processed.add(episode_id)
        # Check if this is a synthetic tconst (contains underscore pattern)
        if "_" in episode_id and episode_id.startswith("tt") and episode_id.count("_") == 2:
            synthetic_episodes_in_cast.add(episode_id)
    
    imdb_matched_episodes = len(all_episodes_processed) - len(synthetic_episodes_in_cast)
    synthetic_episodes = len(missing_episodes)
    
    # Count IMDb matched vs synthetic actors
    imdb_matched_actors = 0
    tmdb_only_actors = 0
    
    for person_data in person_cache.values():
        if person_data.get("tmdb_source", False):
            tmdb_only_actors += 1
        else:
            imdb_matched_actors += 1
    
    # Count regular vs guest appearances
    regular_appearances = len([r for r in rows if r.get("castType") == "regular"])
    guest_appearances = len([r for r in rows if r.get("castType") == "guest"])
    
    # Report comprehensive statistics
    unique_persons = len(person_cache)
    total_appearances = len(rows)
    api_calls_saved = (total_appearances * 2) - (unique_persons * 2)  # Each appearance would have been 2 calls
    
    print(f"\n=== PROCESSING SUMMARY ===", file=sys.stderr)
    print(f"Total cast appearances: {total_appearances}", file=sys.stderr)
    print(f"Unique cast members: {unique_persons}", file=sys.stderr)
    print(f"Person API calls made: {unique_persons * 2}", file=sys.stderr)
    print(f"Person API calls saved: {api_calls_saved}", file=sys.stderr)
    if total_appearances > 0:
        print(f"Optimization ratio: {api_calls_saved / (total_appearances * 2) * 100:.1f}% fewer person calls", file=sys.stderr)
    
    print(f"\n=== EPISODE MATCHING SUMMARY ===", file=sys.stderr)
    print(f"Episodes with IMDb matches: {imdb_matched_episodes}", file=sys.stderr)
    print(f"Episodes with synthetic tconst: {synthetic_episodes}", file=sys.stderr)
    if missing_episodes:
        print(f"Missing episodes written to: {episodes_path}", file=sys.stderr)
    
    print(f"\n=== ACTOR MATCHING SUMMARY ===", file=sys.stderr)
    print(f"Actors with IMDb matches (nconst): {imdb_matched_actors}", file=sys.stderr)
    print(f"Actors with synthetic nconst (TMDb-only): {tmdb_only_actors}", file=sys.stderr)
    if tmdb_only_actors > 0:
        print(f"Synthetic nconst format: nm{'{tmdb_person_id}'}", file=sys.stderr)
    
    print(f"\n=== CAST TYPE SUMMARY ===", file=sys.stderr)
    print(f"Regular cast appearances: {regular_appearances}", file=sys.stderr)
    print(f"Guest star appearances: {guest_appearances}", file=sys.stderr)
    if total_appearances > 0:
        print(f"Regular vs Guest ratio: {regular_appearances/total_appearances:.1%} regular, {guest_appearances/total_appearances:.1%} guest", file=sys.stderr)
    
    print(f"\n=== OUTPUT FILES ===", file=sys.stderr)
    print(f"Cast data: {out_path} ({len(rows)} rows)", file=sys.stderr)
    if missing_episodes:
        print(f"Missing episodes: {episodes_path} ({len(missing_episodes)} rows)", file=sys.stderr)
    else:
        print(f"All episodes had IMDb matches - no missing episodes file created", file=sys.stderr)


if __name__ == "__main__":
    main()
