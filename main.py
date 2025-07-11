import pandas as pd
from pathlib import Path

# Path to data folder
data_dir = Path("IMDB-files")

# Load title.basics.tsv
basics_path = data_dir / "title.basics.tsv"
basics = pd.read_csv(basics_path, sep='\t', dtype=str, na_values='\\N')

# Cozy mystery shows to search for
cozy_titles = [
    "Midsomer Murders", "Father Brown", "Death in Paradise",
    "Agatha Raisin", "Miss Marple", "Grantchester", "Vera", "Poirot"
]

# Filter for cozy series
cozy_shows = basics[
    basics["titleType"].isin(["tvSeries", "tvMiniSeries"]) &
    basics["primaryTitle"].isin(cozy_titles)
]

# Show result
print("Cozy mystery series found:")
print(cozy_shows[["tconst", "primaryTitle", "startYear"]])

# Optional: Save to CSV for reuse
cozy_shows.to_csv("cozy_shows.csv", index=False)
