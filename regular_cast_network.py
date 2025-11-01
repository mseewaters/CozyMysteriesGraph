import os
import streamlit as st
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ---------- Config ----------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "please-set-password")
NEO4J_DB = os.getenv("NEO4J_DATABASE", "neo4j")

# ---------- Neo4j helper ----------
@st.cache_resource(show_spinner=False)
def get_driver(uri, user, pwd):
    return GraphDatabase.driver(uri, auth=(user, pwd))

def run_query(sess, cypher, params=None):
    params = params or {}
    res = sess.run(cypher, **params)
    return [r.data() for r in res]

# ---------- Cypher Queries ----------
CY_ALL_SERIES = """
MATCH (s:Series)
RETURN s.tconst AS tconst, coalesce(s.primaryTitle, s.tconst) AS title
ORDER BY title
"""

CY_ALL_REGULAR_CAST_SORTED_BY_SERIES = """
// Get all regular cast members across all series, sorted by selected series first
MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WHERE r.castType = 'regular'
WITH a, s, collect(r.character) AS characters, count(e) AS episodeCount
WITH a, s, episodeCount,
     [char IN characters WHERE char IS NOT NULL AND char <> '[]' AND char <> '' | char][0] AS mainCharacter
WITH a, s, mainCharacter, episodeCount,
     CASE WHEN s.tconst = $seriesTconst THEN 0 ELSE 1 END AS sortOrder
RETURN DISTINCT a.nconst AS nconst, 
       a.primaryName AS name,
       coalesce(mainCharacter, 'Unknown Character') AS mainCharacter,
       s.primaryTitle AS seriesName,
       episodeCount,
       sortOrder
ORDER BY sortOrder, s.primaryTitle, a.primaryName
"""

# Fallback query if castType is not available
CY_ALL_FREQUENT_CAST_SORTED_BY_SERIES = """
// Fallback: Use actors with 5+ episodes as proxy for regular cast
MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s, count(e) AS episode_count, collect(r.character)[0] AS mainCharacter
WHERE episode_count >= 5
WITH a, s, mainCharacter, episode_count,
     CASE WHEN s.tconst = $seriesTconst THEN 0 ELSE 1 END AS sortOrder
RETURN DISTINCT a.nconst AS nconst, 
       a.primaryName AS name,
       coalesce(mainCharacter, 'Unknown Character') AS mainCharacter,
       s.primaryTitle AS seriesName,
       episode_count AS episodeCount,
       sortOrder
ORDER BY sortOrder, s.primaryTitle, episode_count DESC, a.primaryName
"""

CY_CHECK_CASTTYPE_AVAILABILITY = """
MATCH ()-[r:ACTED_IN]->()
WHERE r.castType IS NOT NULL
RETURN count(r) > 0 AS hasCastType
"""

CY_SHORTEST_PATH = """
MATCH (a1:Actor {nconst: $actor1}), (a2:Actor {nconst: $actor2})
MATCH path = shortestPath((a1)-[*]-(a2))
WHERE ALL(rel IN relationships(path) WHERE type(rel) = 'ACTED_IN' OR type(rel) = 'CO_STARRED_WITH')
RETURN length(path) AS pathLength, path
"""

CY_SHORTEST_PATH_VIA_EPISODES = """
MATCH (a1:Actor {nconst: $actor1}), (a2:Actor {nconst: $actor2})
MATCH path = shortestPath((a1)-[:ACTED_IN*..10]-(a2))
WHERE ALL(node IN nodes(path) WHERE node:Actor OR node:Episode)
RETURN length(path) AS pathLength
"""

CY_CONNECTION_VIA_COSTARRED = """
MATCH (a1:Actor {nconst: $actor1})-[r:CO_STARRED_WITH]-(a2:Actor {nconst: $actor2})
RETURN r.count AS sharedEpisodes, r.series AS seriesName
"""

CY_CONNECTION_STRENGTH_ALL_SERIES = """
MATCH (a1:Actor {nconst: $actor1})-[:ACTED_IN]->(e:Episode)<-[:ACTED_IN]-(a2:Actor {nconst: $actor2})
MATCH (e)-[:PART_OF]->(s:Series)
WITH s, count(DISTINCT e) AS episodeCount
ORDER BY episodeCount DESC
WITH collect({series: s.primaryTitle, episodes: episodeCount}) AS seriesConnections,
     sum(episodeCount) AS totalEpisodes
RETURN totalEpisodes,
       seriesConnections[0] AS primaryConnection,
       size(seriesConnections) AS seriesCount
"""

CY_COMMON_EPISODES_ALL_SERIES = """
MATCH (a1:Actor {nconst: $actor1})-[:ACTED_IN]->(e:Episode)<-[:ACTED_IN]-(a2:Actor {nconst: $actor2})
MATCH (e)-[:PART_OF]->(s:Series)
WITH s, count(DISTINCT e) AS episodeCount, collect(DISTINCT e.primaryTitle)[0..3] AS sampleEpisodes
ORDER BY episodeCount DESC
RETURN sum(episodeCount) AS totalCommonEpisodes,
       collect({series: s.primaryTitle, episodes: episodeCount, samples: sampleEpisodes})[0] AS topSeries
"""

# ---------- UI ----------
st.set_page_config(page_title="Regular Cast Network Analysis", layout="wide")

# Custom CSS for compact layout
st.markdown("""
<style>
.block-container { padding-top: 1rem !important; }
.stSidebar .element-container { margin-bottom: 0.5rem !important; }
.stSidebar h3 { margin: 0.5rem 0 !important; }
.connection-metric { 
    font-size: 1.2em; 
    font-weight: bold; 
    color: #1f77b4; 
    text-align: center;
    background: #f0f8ff;
    padding: 0.5rem;
    border-radius: 0.5rem;
    margin: 0.2rem 0;
}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🎭 Regular Cast Network")
    st.markdown("Analyze connections between regular cast members")
    
    # Connection settings
    with st.expander("⚙️ Neo4j Connection", expanded=False):
        st.text_input("URI", value=NEO4J_URI, key="uri")
        st.text_input("User", value=NEO4J_USER, key="user")
        st.text_input("Password", value=NEO4J_PASSWORD, type="password", key="pwd")
        st.text_input("Database", value=NEO4J_DB, key="db")
        if st.button("Reconnect"):
            st.cache_resource.clear()
            st.rerun()

    st.markdown("#### Select Series")
    
    # Get connection settings
    current_uri = st.session_state.get("uri", NEO4J_URI)
    current_user = st.session_state.get("user", NEO4J_USER)
    current_password = st.session_state.get("pwd", NEO4J_PASSWORD)
    current_db = st.session_state.get("db", NEO4J_DB)

    # Get Neo4j driver
    driver = get_driver(current_uri, current_user, current_password)

    # Series selector
    with driver.session(database=current_db) as sess:
        series_rows = run_query(sess, CY_ALL_SERIES)

    if not series_rows:
        st.warning("No series found in database.")
        st.info("Make sure to import your data with castType information.")
        st.stop()

    series_options = {f"{r['title']}": r['tconst'] for r in series_rows}
    selected_series_name = st.selectbox("📺 Series:", list(series_options.keys()))
    selected_series_tconst = series_options[selected_series_name]

# Check if castType information is available and get regular cast
has_casttype = False
cast_method = ""

with driver.session(database=current_db) as sess:
    try:
        casttype_check = run_query(sess, CY_CHECK_CASTTYPE_AVAILABILITY)
        has_casttype = casttype_check[0]['hasCastType'] if casttype_check else False
        
        if has_casttype:
            # Use regular castType query
            regular_cast = run_query(sess, CY_ALL_REGULAR_CAST_SORTED_BY_SERIES, {"seriesTconst": selected_series_tconst})
            cast_method = "castType filter"
        else:
            # Fallback to frequent cast members
            regular_cast = run_query(sess, CY_ALL_FREQUENT_CAST_SORTED_BY_SERIES, {"seriesTconst": selected_series_tconst})
            cast_method = "frequent appearances (5+ episodes)"
            st.info("⚠️ No castType information found. Using frequent cast members (5+ episodes) as approximation.")
            
    except Exception as e:
        st.error(f"Database query error: {e}")
        st.stop()

if not regular_cast:
    st.warning("No regular cast found for this series.")
    if cast_method == "castType filter":
        st.info("""
        **No regular cast members found with castType='regular'.**
        
        This might mean:
        1. The data wasn't imported with castType information, or
        2. This series doesn't have any actors marked as 'regular' cast
        
        **To add castType information to your Neo4j database:**
        Run the `update_neo4j_casttype.py` script to import castType data from cleaned_episode_cast.csv
        """)
    else:
        st.info("No actors found with 5+ episodes in this series.")
    st.stop()

# Main layout
st.markdown(f"## 🎭 Regular Cast Network: **{selected_series_name}**")

# Show method used
if 'cast_method' in locals():
    if cast_method == "castType filter":
        st.success("✅ Using castType='regular' filter")
    else:
        st.info(f"ℹ️ Using {cast_method}")

# Two-column layout
left_col, right_col = st.columns([1, 2])

with left_col:
    st.markdown("### 👥 Select Actor")
    
    # Create radio button options for actors
    actor_options = []
    for actor in regular_cast:
        character_text = actor.get('mainCharacter', 'Unknown Character')
        series_name = actor.get('seriesName', '')
        episode_count = actor.get('episodeCount', 0)
        
        if series_name:
            actor_options.append(f"**{actor['name']}** ({series_name})\n_{character_text}_ • {episode_count} episodes")
        else:
            actor_options.append(f"**{actor['name']}**\n_{character_text}_")
    
    if len(regular_cast) == 0:
        st.info("No regular cast members found.")
        st.stop()
    
    # Actor selection
    selected_actor_idx = st.radio(
        "Choose a regular cast member:",
        range(len(regular_cast)),
        format_func=lambda i: actor_options[i],
        key="actor_radio"
    )
    
    selected_actor = regular_cast[selected_actor_idx]

with right_col:
    st.markdown("### 🔗 Network Connections")
    
    if len(regular_cast) < 2:
        st.info("Need at least 2 regular cast members to show connections.")
    else:
        st.markdown(f"**From: {selected_actor['name']}**")
        
        # Calculate connections to all other regular cast members
        connections = []
        
        with driver.session(database=current_db) as sess:
            for other_actor in regular_cast:
                if other_actor['nconst'] == selected_actor['nconst']:
                    continue
                
                # Try different methods to find connections
                connection_strength = 0
                connection_type = "No connection"
                details = ""
                
                # Method 1: Check for connections across ALL series
                connection_result = run_query(sess, CY_CONNECTION_STRENGTH_ALL_SERIES, {
                    "actor1": selected_actor['nconst'], 
                    "actor2": other_actor['nconst']
                })
                
                if connection_result and connection_result[0].get('totalEpisodes', 0) > 0:
                    total_eps = connection_result[0]['totalEpisodes']
                    primary_conn = connection_result[0].get('primaryConnection', {})
                    series_count = connection_result[0].get('seriesCount', 1)
                    
                    # Calculate connection strength based on total episodes and series span
                    if total_eps >= 10:
                        connection_strength = 5
                        connection_type = "Very Strong"
                    elif total_eps >= 5:
                        connection_strength = 4
                        connection_type = "Strong"
                    elif total_eps >= 3:
                        connection_strength = 3
                        connection_type = "Moderate"
                    elif total_eps >= 1:
                        connection_strength = 2
                        connection_type = "Weak"
                    else:
                        connection_strength = 1
                        connection_type = "Minimal"
                    
                    # Create details string
                    if series_count == 1:
                        details = f"{total_eps} episodes in {primary_conn.get('series', 'Unknown Series')}"
                    else:
                        details = f"{total_eps} episodes across {series_count} series (strongest: {primary_conn.get('episodes', 0)} in {primary_conn.get('series', 'Unknown')})"
                else:
                    # No direct episodes together, try shortest path calculation
                    try:
                        path_result = run_query(sess, CY_SHORTEST_PATH_VIA_EPISODES, {
                            "actor1": selected_actor['nconst'], 
                            "actor2": other_actor['nconst']
                        })
                        
                        if path_result and path_result[0].get('pathLength') is not None:
                            path_length = path_result[0]['pathLength']
                            # Convert relationship hops to "degrees of separation"
                            degrees = (path_length + 1) // 2  # Each actor-episode-actor = 2 hops = 1 degree
                            connection_strength = max(1, 6 - degrees)  # Inverse relationship
                            connection_type = f"{degrees} degrees"
                            details = f"Connected via {degrees} degrees of separation"
                        else:
                            connection_strength = 0
                            connection_type = "No path found"
                            details = "No connection found in graph"
                    except Exception as e:
                        connection_strength = 0
                        connection_type = "Error calculating"
                        details = f"Error: {str(e)}"
                
                connections.append({
                    'actor': other_actor,
                    'strength': connection_strength,
                    'type': connection_type,
                    'details': details
                })
        
        # Sort by connection strength (strongest first)
        connections.sort(key=lambda x: x['strength'], reverse=True)
        
        # Display connections
        st.markdown("#### Connection Strength")
        
        for conn in connections:
            actor = conn['actor']
            character_text = actor.get('mainCharacter', 'Unknown Character')
            series_name = actor.get('seriesName', '')
            
            # Color code based on connection strength
            if conn['strength'] >= 4:
                color = "#2e8b57"  # Strong green
            elif conn['strength'] >= 2:
                color = "#ffa500"  # Orange
            elif conn['strength'] >= 1:
                color = "#ff6b6b"  # Light red
            else:
                color = "#lightgray"  # Gray for no connection
            
            display_name = f"{actor['name']} ({series_name})" if series_name else actor['name']
            
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding-left: 10px; margin: 5px 0;">
                <strong>{display_name}</strong><br>
                <em>{character_text}</em><br>
                <small>{conn['type']} - {conn['details']}</small>
            </div>
            """, unsafe_allow_html=True)

# Additional info section
st.markdown("---")
with st.expander("ℹ️ About Network Analysis", expanded=False):
    st.markdown("""
    **How It Works:**
    
    **Actor List (Left Side):**
    - Shows only regular cast members from the selected series
    - Displays their most common character name from that series
    - Series selection is used to filter which regular actors to show
    
    **Connection Analysis (Right Side):**
    - Calculates connections across **ALL series and episodes** in the database
    - Includes both regular and guest appearances for comprehensive network analysis
    - Connection strength based on total shared episodes across all shows
    
    **Connection Types:**
    - **Very Strong** (5): 10+ shared episodes across all series
    - **Strong** (4): 5-9 shared episodes
    - **Moderate** (3): 3-4 shared episodes  
    - **Weak** (2): 1-2 shared episodes
    - **X degrees**: Actors connected indirectly through other actors
    - **No connection**: No path found between actors
    
    **Why This Approach:**
    - Actor list focuses on the series you're interested in
    - Connection analysis is comprehensive across their entire careers
    - Shows how actors from one series connect to the broader cozy mystery universe
    
    **To add castType to existing Neo4j data:**
    Run the `update_neo4j_casttype.py` script, or manually:
    ```cypher
    LOAD CSV WITH HEADERS FROM 'file:///cleaned_episode_cast.csv' AS row
    MATCH (a:Actor {nconst: row.nconst})-[r:ACTED_IN]->(e:Episode {tconst: row.tconst})
    SET r.castType = row.castType
    ```
    """)