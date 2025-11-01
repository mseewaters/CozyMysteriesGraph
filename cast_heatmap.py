import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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

CY_SERIES_LIST = """
// Get all series that have regular cast members
MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WHERE r.castType = 'regular'
WITH s, count(DISTINCT a) AS regularCastCount
WHERE regularCastCount > 0
RETURN s.tconst AS tconst,
       s.primaryTitle AS title,
       regularCastCount
ORDER BY s.primaryTitle
"""

CY_SERIES_CONNECTION_MATRIX = """
// Get cross-series connections aggregated by series pairs with castType filter
WITH $series AS seriesList
UNWIND seriesList AS series1
UNWIND seriesList AS series2
WITH series1, series2
WHERE series1.tconst < series2.tconst

// Find actors who appear in both series
MATCH (a:Actor)-[r1:ACTED_IN]->(e1:Episode)-[:PART_OF]->(s1:Series {tconst: series1.tconst})
MATCH (a)-[r2:ACTED_IN]->(e2:Episode)-[:PART_OF]->(s2:Series {tconst: series2.tconst})

// Apply cast type filter
WHERE ($castTypeFilter = 'all' OR r1.castType = $castTypeFilter OR r2.castType = $castTypeFilter)

WITH series1, series2, a,
     count(DISTINCT e1) AS series1Episodes,
     count(DISTINCT e2) AS series2Episodes,
     collect(DISTINCT r1.castType)[0] AS castType1,
     collect(DISTINCT r2.castType)[0] AS castType2

WITH series1, series2, a, series1Episodes, series2Episodes,
     CASE 
         WHEN castType1 IS NOT NULL THEN castType1 
         ELSE castType2 
     END AS primaryCastType,
     series1Episodes + series2Episodes AS totalEpisodes

WITH series1, series2,
     collect({
         actor: a.primaryName,
         episodes: totalEpisodes,
         castType: primaryCastType
     }) AS actorBreakdown,
     count(DISTINCT a) AS uniqueActorsCrossing,
     sum(totalEpisodes) AS totalCrossoverEpisodes

WHERE uniqueActorsCrossing > 0

RETURN series1.tconst AS series1_tconst,
       series1.title AS series1_title,
       series2.tconst AS series2_tconst,
       series2.title AS series2_title,
       totalCrossoverEpisodes,
       uniqueActorsCrossing,
       actorBreakdown
"""

CY_CHECK_CASTTYPE_AVAILABILITY = """
MATCH ()-[r:ACTED_IN]->()
WHERE r.castType IS NOT NULL
RETURN count(r) > 0 AS hasCastType
"""

# ---------- Helper Functions ----------
@st.cache_data
def get_series_data(_driver, database):
    """Get all series with regular cast members"""
    with _driver.session(database=database) as sess:
        # Check if castType is available
        casttype_check = run_query(sess, CY_CHECK_CASTTYPE_AVAILABILITY)
        has_casttype = casttype_check[0]['hasCastType'] if casttype_check else False
        
        if not has_casttype:
            st.error("❌ No castType information found in the database. Please reimport with castType data.")
            return None, False
        
        series_list = run_query(sess, CY_SERIES_LIST)
        return series_list, True

@st.cache_data
def get_series_connection_matrix(_driver, database, series_list, cast_type_filter="all"):
    """Get cross-series connection matrix aggregated by series with cast type filter"""
    if not series_list:
        return []
    
    with _driver.session(database=database) as sess:
        # Prepare series list for query
        series_params = [{"tconst": series['tconst'], "title": series['title']} for series in series_list]
        connections = run_query(sess, CY_SERIES_CONNECTION_MATRIX, {
            "series": series_params,
            "castTypeFilter": cast_type_filter
        })
        return connections

def create_series_heatmap(series_list, connections, cast_type_filter="all"):
    """Create interactive heatmap of series-to-series connections"""
    if not series_list or len(series_list) < 2:
        st.warning("Need at least 2 series to create a heatmap")
        return None
    
    # Create series lookup
    series_lookup = {series['tconst']: i for i, series in enumerate(series_list)}
    n_series = len(series_list)
    
    # Initialize connection matrix
    matrix = np.zeros((n_series, n_series))
    hover_text = [["" for j in range(n_series)] for i in range(n_series)]
    
    # Initialize all hover text first
    for i in range(n_series):
        for j in range(n_series):
            if i == j:
                # Diagonal
                hover_text[i][j] = f"{series_list[i]['title']}<br>({series_list[i]['regularCastCount']} regular cast)"
            elif i < j:
                # Upper triangle - will be filled with actual data
                hover_text[i][j] = f"{series_list[i]['title']}<br>{series_list[j]['title']}<br>No cross-series connections"
            else:
                # Lower triangle - empty for masking
                hover_text[i][j] = ""
    
    # Fill in connections (upper triangle only to avoid duplication)
    for conn in connections:
        series1_idx = series_lookup.get(conn['series1_tconst'])
        series2_idx = series_lookup.get(conn['series2_tconst'])
        
        if series1_idx is not None and series2_idx is not None:
            # Use number of unique actors crossing over as the connection strength
            connection_strength = conn['uniqueActorsCrossing']
            episodes = conn['totalCrossoverEpisodes']
            
            # Always put in upper triangle: ensure i < j
            i, j = min(series1_idx, series2_idx), max(series1_idx, series2_idx)
            matrix[i, j] = connection_strength
            
            # Create detailed hover text with cast type information
            actor_details = []
            for actor_info in conn['actorBreakdown'][:5]:  # Show top 5
                cast_type = actor_info.get('castType', 'unknown')
                cast_type_icon = "⭐" if cast_type == "regular" else "👥" if cast_type == "guest" else "❓"
                actor_details.append(f"{cast_type_icon} {actor_info['actor']}: {actor_info['episodes']} eps")
            
            if len(conn['actorBreakdown']) > 5:
                actor_details.append("...")
                
            filter_label = {
                "all": "All actors",
                "regular": "Regular cast",
                "guest": "Guest stars"
            }.get(cast_type_filter, "Actors")
                
            # Update hover text for the upper triangle position
            hover_text[i][j] = (
                f"{series_list[i]['title']}<br>"
                f"{series_list[j]['title']}<br>"
                f"{connection_strength} {filter_label.lower()} crossing over<br>"
                f"{episodes} total episodes<br>"
                f"Connections:<br>" + "<br>".join(actor_details)
            )
    
    # Mask the lower triangle and set diagonal values
    for i in range(n_series):
        for j in range(n_series):
            if i == j:
                # Diagonal - set to 0 and show series info
                matrix[i, j] = 0
                hover_text[i][j] = f"{series_list[i]['title']}<br>({series_list[i]['regularCastCount']} regular cast)"
            elif i > j:
                # Lower triangle - mask it completely
                matrix[i, j] = np.nan
                hover_text[i][j] = ""
    
    # Create labels with just series titles
    labels = [series['title'] for series in series_list]
    
    # Dynamic title based on filter
    title_map = {
        "all": "All Actor Cross-Connections",
        "regular": "Regular Cast Cross-Connections", 
        "guest": "Guest Star Cross-Connections"
    }
    
    colorbar_title_map = {
        "all": "Actors Crossing Over",
        "regular": "Regulars Crossing Over",
        "guest": "Guests Crossing Over"
    }
    
    # Create heatmap with custom colorscale that handles NaN values
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=labels,
        y=labels,
        text=hover_text,
        texttemplate="%{text}",
        hovertemplate="%{text}<extra></extra>",
        colorscale='Viridis',
        showscale=True,
        colorbar=dict(title=colorbar_title_map[cast_type_filter]),
        hoverongaps=False,  # Don't show hover on NaN/masked cells
        zmin=0  # Set minimum to 0 to ensure proper color scaling
    ))
    
    fig.update_layout(
        title=f"Series {title_map[cast_type_filter]} Network",
        xaxis_title="Series",
        yaxis_title="Series", 
        width=800,
        height=800,
        xaxis={'side': 'bottom', 'tickangle': 45},
        yaxis={'side': 'left'},
        # Improve appearance for triangular matrix
        plot_bgcolor='white'
    )
    
    return fig

# ---------- UI ----------
st.set_page_config(page_title="Cast Network Heatmap", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 1rem !important; }
.stSidebar .element-container { margin-bottom: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🎭 Series Connection Network")
    st.markdown("Shows how different cozy mystery series are connected through shared actors")
    
    # Connection settings
    with st.expander("⚙️ Neo4j Connection", expanded=False):
        st.text_input("URI", value=NEO4J_URI, key="uri")
        st.text_input("User", value=NEO4J_USER, key="user")
        st.text_input("Password", value=NEO4J_PASSWORD, type="password", key="pwd")
        st.text_input("Database", value=NEO4J_DB, key="db")
        if st.button("Reconnect"):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()

    # Get connection settings
    current_uri = st.session_state.get("uri", NEO4J_URI)
    current_user = st.session_state.get("user", NEO4J_USER)
    current_password = st.session_state.get("pwd", NEO4J_PASSWORD)
    current_db = st.session_state.get("db", NEO4J_DB)

    # Get Neo4j driver
    driver = get_driver(current_uri, current_user, current_password)

    st.markdown("#### Filter Options")

# Main content
st.markdown("## 🎭 Series Connection Network Heatmap")
st.markdown("*Shows how different cozy mystery series are connected through actors crossing between them*")

# Get series data
try:
    with st.spinner("Loading series data..."):
        series_list, has_data = get_series_data(driver, current_db)
    
    if not has_data or not series_list:
        st.stop()
        
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.info("Please check your Neo4j connection settings in the sidebar.")
    st.stop()

with st.sidebar:
    st.markdown("#### Connection Type Filter")
    
    cast_type_filter = st.selectbox(
        "Show connections for:",
        options=["all", "regular", "guest"],
        format_func=lambda x: {
            "all": "🎭 All Actors",
            "regular": "⭐ Regular Cast Only", 
            "guest": "👥 Guest Stars Only"
        }[x],
        help="Filter which types of actors to show connections for"
    )
    
    st.markdown("---")
    st.markdown(f"**Series with regulars:** {len(series_list)}")
    total_regular_cast = sum(series['regularCastCount'] for series in series_list)
    st.markdown(f"**Total regular cast:** {total_regular_cast}")
    
    # Show filter explanation
    if cast_type_filter == "regular":
        st.info("Showing only regular cast members who appeared in other series")
    elif cast_type_filter == "guest":
        st.info("Showing only guest stars who appeared in multiple series")
    else:
        st.info("Showing all actor connections between series")

# Get connections with filter
try:
    with st.spinner(f"Calculating {cast_type_filter} connections..."):
        connections = get_series_connection_matrix(driver, current_db, series_list, cast_type_filter)
        
except Exception as e:
    st.error(f"Error calculating connections: {e}")
    st.stop()

# Create and display heatmap
fig = create_series_heatmap(series_list, connections, cast_type_filter)

if fig:
    st.plotly_chart(fig, use_container_width=True)
    
    # Show statistics based on filter
    col1, col2, col3 = st.columns(3)
    
    filter_labels = {
        "all": "Actor",
        "regular": "Regular Cast",
        "guest": "Guest Star"
    }
    
    label = filter_labels[cast_type_filter]
    
    with col1:
        total_connections = len([c for c in connections if c['uniqueActorsCrossing'] > 0])
        st.metric(f"Connected Series Pairs", total_connections)
    
    with col2:
        if connections:
            max_actors_crossing = max((c['uniqueActorsCrossing'] for c in connections), default=0)
            st.metric(f"Max {label}s Crossing", max_actors_crossing)
        else:
            st.metric(f"Max {label}s Crossing", 0)
    
    with col3:
        total_possible_pairs = len(series_list) * (len(series_list) - 1) // 2
        connection_density = (total_connections / total_possible_pairs * 100) if total_possible_pairs > 0 else 0
        st.metric(f"{label} Network Density", f"{connection_density:.1f}%")
        
    # Show top connected series pairs
    if connections:
        filter_title = {
            "all": "🔗 Top Connected Series Pairs (All Actors)",
            "regular": "⭐ Top Connected Series Pairs (Regular Cast)",
            "guest": "� Top Connected Series Pairs (Guest Stars)"
        }
        
        st.markdown(f"### {filter_title[cast_type_filter]}")
        sorted_connections = sorted(connections, key=lambda x: x['uniqueActorsCrossing'], reverse=True)[:5]
        
        for i, conn in enumerate(sorted_connections):
            actor_count = conn['uniqueActorsCrossing']
            label_text = f"{filter_labels[cast_type_filter].lower()}s" if actor_count != 1 else filter_labels[cast_type_filter].lower()
            
            with st.expander(f"{i+1}. {conn['series1_title']} ↔ {conn['series2_title']} ({actor_count} {label_text})", expanded=i==0):
                st.markdown(f"**Total crossover episodes:** {conn['totalCrossoverEpisodes']}")
                st.markdown(f"**{filter_labels[cast_type_filter]}s crossing over:**")
                for actor_info in conn['actorBreakdown']:
                    cast_type = actor_info.get('castType', 'unknown')
                    cast_type_icon = "⭐" if cast_type == "regular" else "👥" if cast_type == "guest" else "❓"
                    st.markdown(f"- {cast_type_icon} {actor_info['actor']}: {actor_info['episodes']} episodes")
else:
    st.info("Need at least 2 series to create a heatmap.")

# Information section
with st.expander("ℹ️ How to Read the Series Network Heatmap", expanded=False):
    st.markdown("""
    **What This Shows:**
    - **Series-to-Series Connections**: How different cozy mystery series are connected through shared actors
    - **Aggregated View**: Instead of individual actors, shows relationships between entire series
    - **Cross-Pollination**: Regular cast from one series appearing in other series
    
    **Reading the Heatmap:**
    - **Darker colors** = More actors have crossed between these series
    - **Color intensity** = Number of different actors who have worked in both series
    - **Black/Zero** = No actors have crossed between these series
    - **Hover** for details on which actors and how many episodes
    
    **Key Insights:**
    - **Series Clusters**: Groups of series that share many actors
    - **Isolated Series**: Shows that mostly use their own casting pool  
    - **Hub Series**: Shows that serve as bridges to many other series
    - **Network Structure**: The overall connectivity of the cozy mystery universe
    
    **Example Connections:**
    - If 3 Inspector Morse regulars appeared as guests in Midsomer Murders, the cell shows "3"
    - The hover shows which actors and how many episodes they crossed over in
    
    **Strategic Value:**
    - **Casting Networks**: Which series draw from similar actor pools
    - **Genre Evolution**: How the cozy mystery ecosystem has developed
    - **Cross-Promotion**: Series that might appeal to similar audiences
    - **Production Insights**: Reveals shared casting directors or production companies
    
    **Filter Options:**
    - **⭐ Regular Cast Only**: Shows regular cast members who crossed over to other series (career moves, guest appearances)
    - **👥 Guest Stars Only**: Shows guest actors who appeared in multiple series (freelance actors, recurring guests)
    - **🎭 All Actors**: Shows all cross-series connections regardless of cast type
    
    **Why Filter Matters:**
    - **Regular Cast Filter**: Reveals career paths, spin-offs, and series transitions
    - **Guest Star Filter**: Shows the freelance actor network and multi-series guest performers
    - **All Actors**: Complete picture of series interconnectedness
    
    **Measurement**: Connection strength = number of unique actors of the selected type who crossed between series.
    """)