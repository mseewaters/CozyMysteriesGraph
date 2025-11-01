import pandas as pd
import questionary
from pathlib import Path

# --- Setup ---
# Set up directory paths relative to the project root
project_root = Path(__file__).parent.parent
data_dir = project_root / "IMDB-files"
output_dir = project_root / "GraphDB-files"

# Create output directory if it doesn't exist
output_dir.mkdir(exist_ok=True)

# Cozy series to include
cozy_titles = [
    "Midsomer Murders", "Father Brown", "Death in Paradise",
    "Shakespeare & Hathaway: Private Investigators", "McDonald & Dodds", "Miss Fisher's Murder Mysteries", "Endeavour",
    "New Tricks", "Inspector Morse", "The Madame Blanc Mysteries","Professor T", "Shetland", "Ludwig"
]

# --- Load title.basics and filter series ---
basics = pd.read_csv(data_dir / "title.basics.tsv", sep='\t', dtype=str, na_values='\\N')

# All series matching the initial title list (but don't filter yet)
all_candidates = basics[
    basics['titleType'].isin(['tvSeries', 'tvMiniSeries']) &
    basics['primaryTitle'].isin(cozy_titles)
].copy()

# --- Let user choose series to include ---
choices = [
    questionary.Choice(
        title=f"{row['primaryTitle']} ({row['startYear']}) [{row['genres']}]", 
        value=row['tconst']
    )
    for _, row in all_candidates.iterrows()
]

selected_series_ids = questionary.checkbox(
    "Select which cozy series to include:",
    choices=choices
).ask()

# Filter to selected series only
cozy_shows = all_candidates[all_candidates['tconst'].isin(selected_series_ids)].copy()
cozy_series_ids = cozy_shows['tconst'].tolist()

print(cozy_shows)

# --- Load episode mapping and filter for cozy series ---
episodes = pd.read_csv(data_dir / "title.episode.tsv", sep='\t', dtype=str, na_values='\\N')
cozy_episodes = episodes[episodes['parentTconst'].isin(cozy_series_ids)].copy()

# --- Join to get episode titles and air years ---
cozy_episode_details = cozy_episodes.merge(basics, on="tconst", how="left")
cozy_episode_details = cozy_episode_details[[
    "tconst", "parentTconst", "primaryTitle", "seasonNumber", "episodeNumber", "startYear"
]]

# --- Load ratings and join ---
ratings = pd.read_csv(data_dir / "title.ratings.tsv", sep='\t', dtype=str, na_values='\\N')
cozy_episode_details = cozy_episode_details.merge(ratings, on="tconst", how="left")

print(cozy_episode_details.head)

# --- Load actor mapping (title.principals.tsv) ---
principals = pd.read_csv(data_dir / "title.principals.tsv", sep='\t', dtype=str, na_values='\\N')

# Only keep actors (ignore producers, writers, etc.)
actor_roles = principals[
    (principals['tconst'].isin(cozy_episode_details['tconst'])) &
    (principals['category'].isin(['actor', 'actress']))
].copy()

# --- Load actor names ---
names = pd.read_csv(data_dir / "name.basics.tsv", sep='\t', dtype=str, na_values='\\N')
cozy_actors = actor_roles.merge(names, on='nconst', how='left')

print(cozy_actors.head())

# --- Save all outputs ---
# Save with proper CSV quoting to handle commas in text fields
cozy_shows.to_csv(output_dir / "out_cozy_series.csv", index=False, quoting=1)
cozy_episode_details.to_csv(output_dir / "out_cozy_episodes.csv", index=False, quoting=1)
cozy_actors.to_csv(output_dir / "out_cozy_actors.csv", index=False, quoting=1)

print("✅ All done! Files written:")
print(f"- {output_dir}/out_cozy_series.csv")
print(f"- {output_dir}/out_cozy_episodes.csv")
print(f"- {output_dir}/out_cozy_actors.csv")
