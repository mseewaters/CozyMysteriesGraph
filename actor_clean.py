import streamlit as st
import pandas as pd

# Load data
@st.cache_data
def load_data():
    series_df = pd.read_csv("out_cozy_series.csv")
    episodes_df = pd.read_csv("out_cozy_episodes.csv")
    actors_df = pd.read_csv("out_cozy_actors copy.csv")
    return series_df, episodes_df, actors_df

series_df, episodes_df, actors_df = load_data()

# Select a Series
st.markdown("🎬 **Select a series**")
series_options = series_df[series_df["titleType"] == "tvSeries"]
series_name_to_id = dict(zip(series_options["primaryTitle"], series_options["tconst"]))
selected_series_name = st.selectbox("Select a series", sorted(series_name_to_id.keys()))
selected_series_id = series_name_to_id[selected_series_name]

# Filter for episodes in this series
series_episodes = episodes_df[episodes_df["parentTconst"] == selected_series_id]

# Join actors to episodes
actors_in_series = pd.merge(
    actors_df, 
    series_episodes[["tconst", "seasonNumber", "episodeNumber"]],
    on="tconst", how="inner"
)

# Group to find actors in multiple episodes
multi_ep_actors = (
    actors_in_series.groupby("nconst")
    .filter(lambda x: x["tconst"].nunique() > 1 and x["characters"].nunique() > 1)
    .sort_values(["primaryName", "seasonNumber", "episodeNumber"])
)

# Get list of unique actors
actor_list = (
    multi_ep_actors[["nconst", "primaryName"]]
    .drop_duplicates()
    .sort_values("primaryName")
)

# Sidebar actor selector
st.sidebar.markdown("🎭 **Actors in Multiple Episodes**\nClick an actor:")
actor_choice = st.sidebar.radio(
    "Click an actor:",
    actor_list.apply(lambda row: f"{row['primaryName']} ({row['nconst']})", axis=1)
)

# Extract nconst
selected_nconst = actor_choice.split("(")[-1].replace(")", "")

# Display actor's roles
actor_rows = multi_ep_actors[multi_ep_actors["nconst"] == selected_nconst].copy()
actor_name = actor_rows["primaryName"].iloc[0]

st.markdown(f"### Edit character names for {actor_name} (`{selected_nconst}`) in *{selected_series_name}*")

# Display actor's roles with inline layout
edited_data = []
for _, row in actor_rows.iterrows():
    season = int(row["seasonNumber"])
    episode = int(row["episodeNumber"])
    current_name = row["characters"]
    key = f"{season}-{episode}"

    # Efficient inline layout
    col1, col2 = st.columns([1, 3])
    with col1:
        col1.markdown(f"S{season} Ep{episode}")
    with col2:
        new_name = col2.text_input(
            label=" ", 
            value=current_name, 
            key=key,
            label_visibility="collapsed"
        )

    row["characters"] = new_name
    edited_data.append(row)

# Save button
if st.button("💾 Save"):
    updated_df = pd.DataFrame(edited_data)
    new_actors_df = actors_df.copy()

    # Update character names
    for _, r in updated_df.iterrows():
        mask = (
            (new_actors_df["tconst"] == r["tconst"]) &
            (new_actors_df["nconst"] == r["nconst"])
        )
        new_actors_df.loc[mask, "characters"] = r["characters"]

    new_actors_df.to_csv("out_cozy_actors copy.csv", index=False)
    st.success("✅ Saved to out_cozy_actors copy.csv")
    st.cache_data.clear()  # <--- THIS IS THE FIX
    st.rerun()  # Reloads app fresh
