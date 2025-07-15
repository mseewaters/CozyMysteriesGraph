import pandas as pd
import questionary
from pathlib import Path

# --- Setup ---
data_dir = Path("IMDB-files")

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
