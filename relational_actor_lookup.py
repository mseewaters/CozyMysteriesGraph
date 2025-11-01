#!/usr/bin/env python3
"""
Relational Database Implementation for Actor Lookup
Using PostgreSQL/SQLite with the same functionality as Neo4j version
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Any
import streamlit as st

class RelationalActorDB:
    def __init__(self, db_path: str = "cozy_mysteries.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Create tables and indexes for optimal query performance"""
        conn = sqlite3.connect(self.db_path)
        
        # Create tables
        conn.executescript("""
        -- Series table
        CREATE TABLE IF NOT EXISTS series (
            tconst TEXT PRIMARY KEY,
            primary_title TEXT,
            start_year INTEGER,
            end_year INTEGER,
            genres TEXT
        );
        
        -- Episodes table  
        CREATE TABLE IF NOT EXISTS episodes (
            tconst TEXT PRIMARY KEY,
            parent_tconst TEXT,
            primary_title TEXT,
            season_number INTEGER,
            episode_number INTEGER,
            start_year INTEGER,
            average_rating REAL,
            num_votes INTEGER,
            FOREIGN KEY (parent_tconst) REFERENCES series(tconst)
        );
        
        -- Actors table
        CREATE TABLE IF NOT EXISTS actors (
            nconst TEXT PRIMARY KEY,
            primary_name TEXT,
            birth_year INTEGER,
            death_year INTEGER,
            primary_profession TEXT,
            known_for_titles TEXT
        );
        
        -- Cast/Roles junction table
        CREATE TABLE IF NOT EXISTS episode_cast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_tconst TEXT,
            actor_nconst TEXT,
            character_name TEXT,
            ordering INTEGER,
            category TEXT,
            FOREIGN KEY (episode_tconst) REFERENCES episodes(tconst),
            FOREIGN KEY (actor_nconst) REFERENCES actors(nconst)
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_episodes_parent ON episodes(parent_tconst);
        CREATE INDEX IF NOT EXISTS idx_episodes_season ON episodes(parent_tconst, season_number);
        CREATE INDEX IF NOT EXISTS idx_cast_episode ON episode_cast(episode_tconst);
        CREATE INDEX IF NOT EXISTS idx_cast_actor ON episode_cast(actor_nconst);
        CREATE INDEX IF NOT EXISTS idx_cast_actor_episode ON episode_cast(actor_nconst, episode_tconst);
        """)
        
        conn.close()
    
    def get_all_series(self) -> List[Dict[str, Any]]:
        """Equivalent to CY_ALL_SERIES"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tconst, COALESCE(primary_title, tconst) as title
            FROM series 
            ORDER BY title
        """)
        
        results = [{"tconst": row[0], "title": row[1]} for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_episodes_in_series(self, series_tconst: str) -> List[Dict[str, Any]]:
        """Equivalent to CY_EPISODES_IN_SERIES"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                tconst as etconst,
                COALESCE(primary_title, 'Episode') as title,
                season_number as season,
                episode_number as episode
            FROM episodes 
            WHERE parent_tconst = ?
            ORDER BY season_number, episode_number
        """, (series_tconst,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "etconst": row[0],
                "title": row[1], 
                "season": row[2],
                "episode": row[3]
            })
        
        conn.close()
        return results
    
    def get_cast_for_episode(self, episode_tconst: str) -> List[Dict[str, Any]]:
        """Equivalent to CY_CAST_FOR_EPISODE"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.nconst,
                a.primary_name as name,
                GROUP_CONCAT(
                    CASE 
                        WHEN ec.character_name IS NOT NULL AND ec.character_name != '' 
                        THEN ec.character_name 
                        ELSE '(uncredited/unknown)' 
                    END
                ) as roles
            FROM actors a
            JOIN episode_cast ec ON a.nconst = ec.actor_nconst
            WHERE ec.episode_tconst = ?
            GROUP BY a.nconst, a.primary_name
            ORDER BY a.primary_name
        """, (episode_tconst,))
        
        results = []
        for row in cursor.fetchall():
            roles_str = row[2] or "(uncredited/unknown)"
            roles = roles_str.split(',') if roles_str else ["(uncredited/unknown)"]
            results.append({
                "nconst": row[0],
                "name": row[1],
                "roles": roles
            })
        
        conn.close()
        return results
    
    def get_actor_roles_across_all_series(self, actor_nconst: str) -> List[Dict[str, Any]]:
        """Equivalent to CY_ROLES_VIEW"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Complex query to match Neo4j aggregation logic
        cursor.execute("""
            WITH role_episodes AS (
                SELECT 
                    s.tconst as series_tconst,
                    COALESCE(s.primary_title, s.tconst) as series_title,
                    CASE 
                        WHEN ec.character_name IS NOT NULL AND ec.character_name != '' 
                        THEN ec.character_name 
                        ELSE '(uncredited/unknown)' 
                    END as character,
                    e.season_number,
                    e.episode_number,
                    e.primary_title as episode_title
                FROM actors a
                JOIN episode_cast ec ON a.nconst = ec.actor_nconst  
                JOIN episodes e ON ec.episode_tconst = e.tconst
                JOIN series s ON e.parent_tconst = s.tconst
                WHERE a.nconst = ?
            ),
            character_stats AS (
                SELECT 
                    series_tconst,
                    series_title,
                    character,
                    COUNT(*) as episode_count,
                    json_group_array(
                        json_object(
                            'season', season_number,
                            'episode', episode_number, 
                            'title', episode_title
                        )
                    ) as episodes
                FROM role_episodes
                GROUP BY series_tconst, series_title, character
            )
            SELECT 
                series_tconst,
                series_title,
                character,
                episode_count,
                CASE WHEN episode_count > 2 THEN 'Recurring' ELSE 'Single/Pair' END as label,
                CASE 
                    WHEN episode_count > 2 THEN '[]'
                    ELSE episodes 
                END as sample_episodes
            FROM character_stats
            ORDER BY series_title, character
        """, (actor_nconst,))
        
        results = []
        for row in cursor.fetchall():
            sample_eps = []
            if row[5] != '[]':
                import json
                try:
                    sample_eps = json.loads(row[5])[:2]  # Limit to 2 episodes
                except:
                    sample_eps = []
            
            results.append({
                "seriesTconst": row[0],
                "seriesTitle": row[1], 
                "character": row[2],
                "count": row[3],
                "label": row[4],
                "sampleEpisodes": sample_eps
            })
        
        conn.close()
        return [{"entries": results}]
    
    def load_data_from_csv(self, episodes_csv: str, actors_csv: str, series_csv: str):
        """Load data from your existing CSV files"""
        from pathlib import Path
        
        # Convert to Path objects and make relative to script location if needed
        project_root = Path(__file__).parent
        
        # Handle relative paths
        if not Path(episodes_csv).is_absolute():
            episodes_csv = project_root / episodes_csv
        if not Path(actors_csv).is_absolute():
            actors_csv = project_root / actors_csv
        if not Path(series_csv).is_absolute():
            series_csv = project_root / series_csv
        
        conn = sqlite3.connect(self.db_path)
        
        # Load series data
        series_df = pd.read_csv(series_csv)
        series_df.to_sql('series', conn, if_exists='replace', index=False)
        
        # Load episodes data  
        episodes_df = pd.read_csv(episodes_csv)
        episodes_df.to_sql('episodes', conn, if_exists='replace', index=False)
        
        # Load actors and cast data
        actors_df = pd.read_csv(actors_csv)
        
        # Split into actors table and episode_cast table
        actors_only = actors_df[['nconst', 'primaryName', 'birthYear', 'deathYear', 'primaryProfession', 'knownForTitles']].drop_duplicates('nconst')
        actors_only.columns = ['nconst', 'primary_name', 'birth_year', 'death_year', 'primary_profession', 'known_for_titles']
        actors_only.to_sql('actors', conn, if_exists='replace', index=False)
        
        # Cast relationships
        cast_df = actors_df[['tconst', 'nconst', 'characters', 'ordering', 'category']].copy()
        cast_df.columns = ['episode_tconst', 'actor_nconst', 'character_name', 'ordering', 'category']
        cast_df.to_sql('episode_cast', conn, if_exists='replace', index=False)
        
        conn.close()


# Streamlit app using relational database
def create_relational_streamlit_app():
    st.title("CozyMystery Actor Lookup (Relational DB)")
    
    # Initialize database
    db = RelationalActorDB()
    
    # Load data button
    if st.button("Load Data from CSV"):
        db.load_data_from_csv(
            "GraphDB-files/out_cozy_episodes.csv",
            "GraphDB-files/out_cozy_actors.csv", 
            "GraphDB-files/out_cozy_series.csv"
        )
        st.success("Data loaded successfully!")
    
    # Series selector
    series_data = db.get_all_series()
    if not series_data:
        st.warning("No series found. Load data first.")
        return
    
    series_options = {s["title"]: s["tconst"] for s in series_data}
    selected_series_title = st.selectbox("Series:", list(series_options.keys()))
    selected_series_tconst = series_options[selected_series_title]
    
    # Episode selector
    episodes_data = db.get_episodes_in_series(selected_series_tconst)
    if not episodes_data:
        st.info("No episodes found for this series.")
        return
    
    episode_options = {}
    for ep in episodes_data:
        season = ep.get("season", "?")
        episode = ep.get("episode", "?") 
        label = f"S{season}E{episode} · {ep['title']}"
        episode_options[label] = ep["etconst"]
    
    selected_episode_label = st.selectbox("Episode:", list(episode_options.keys()))
    selected_episode_tconst = episode_options[selected_episode_label]
    
    # Actor selector  
    cast_data = db.get_cast_for_episode(selected_episode_tconst)
    if not cast_data:
        st.info("No cast found for this episode.")
        return
    
    actor_options = {}
    for actor in cast_data:
        roles_str = ", ".join(actor["roles"])
        label = f"{actor['name']} — {roles_str}"
        actor_options[label] = actor["nconst"]
    
    selected_actor_label = st.selectbox("Actor:", list(actor_options.keys()))
    selected_actor_nconst = actor_options[selected_actor_label]
    
    # Show actor roles across all series
    roles_data = db.get_actor_roles_across_all_series(selected_actor_nconst)
    
    if roles_data and roles_data[0].get("entries"):
        selected_actor_name = selected_actor_label.split(" — ")[0]
        st.markdown(f"#### Roles for **{selected_actor_name}**")
        
        entries = roles_data[0]["entries"]
        current_series = None
        
        for entry in entries:
            if current_series != entry["seriesTitle"]:
                current_series = entry["seriesTitle"]
                st.markdown(f"##### {current_series}")
            
            if entry["label"] == "Recurring":
                st.markdown(f"- **{entry['character']}** — Recurring ({entry['count']} eps)")
            else:
                ep_badges = []
                for ep in entry.get("sampleEpisodes", []):
                    ep_badges.append(f"S{ep.get('season')}E{ep.get('episode')}")
                ep_str = ", ".join(ep_badges) if ep_badges else "Single/Pair"
                st.markdown(f"- **{entry['character']}** — {ep_str}")


if __name__ == "__main__":
    create_relational_streamlit_app()