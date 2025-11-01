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

# ---------- Cypher ----------
CY_ALL_SERIES = """
MATCH (s:Series)
RETURN s.tconst AS tconst, coalesce(s.primaryTitle, s.tconst) AS title
ORDER BY title
"""

CY_EPISODES_IN_SERIES = """
MATCH (e:Episode)-[:PART_OF]->(s:Series {tconst:$t})
RETURN e.tconst AS etconst,
       coalesce(e.primaryTitle, 'Episode') AS title,
       e.seasonNumber AS season,
       e.episodeNumber AS episode
ORDER BY season, episode
"""

CY_CAST_FOR_EPISODE = """
MATCH (a:Actor)-[ai:ACTED_IN]->(e:Episode {tconst:$et})
WITH a,
     CASE
       WHEN ai.characters IS NOT NULL THEN ai.characters
       WHEN ai.character  IS NOT NULL THEN [ai.character]
       ELSE ['(uncredited/unknown)']
     END AS roles
RETURN a.nconst AS nconst,
       a.primaryName AS name,
       roles AS roles
ORDER BY name
"""

CY_ROLES_VIEW = """
// Unified roles across ALL series for the selected actor
MATCH (a:Actor {nconst:$n})-[ai:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s, e,
     CASE
       WHEN ai.characters IS NOT NULL THEN ai.characters
       WHEN ai.character  IS NOT NULL THEN [ai.character]
       ELSE ['(uncredited/unknown)']
     END AS roles
UNWIND roles AS role
WITH s, role,
     collect({season:e.seasonNumber, episode:e.episodeNumber, title:e.primaryTitle}) AS eps
WITH s, role, size(eps) AS cnt, eps
RETURN collect({
  seriesTconst: s.tconst,
  seriesTitle: coalesce(s.primaryTitle, s.tconst),
  character: role,
  count: cnt,
  label: CASE WHEN cnt > 2 THEN 'Recurring' ELSE 'Single/Pair' END,
  sampleEpisodes: CASE
    WHEN cnt > 2 THEN []
    ELSE [x IN eps | {season:x.season, episode:x.episode, title:x.title}][0..2]
  END
}) AS entries
"""

# ---------- UI ----------
st.set_page_config(page_title="CozyMystery Roles Lookup", layout="wide")

# Trim top padding/margins and tighten headings
st.markdown("""
<style>
/* Main content container padding (older/newer class names covered) */
.block-container { padding-top: 2rem !important; }
.main .block-container { padding-top: 2rem !important; }        /* newer */
.stMainBlockContainer { padding-top: 2rem !important; }         /* fallback */

/* Reduce title spacing (h1) or hide it and render your own smaller label */
h1 { margin-top: 0.25rem !important; margin-bottom: 0.5rem !important; }

/* Compact sidebar elements */
.css-1d391kg { padding-top: 0.5rem !important; }  /* sidebar top padding */
.stSidebar > div:first-child { padding-top: 0.2rem !important; }
.stSidebar .stSelectbox { margin-bottom: 0.2rem !important; }
.stSidebar .stTextInput { margin-bottom: 0.1rem !important; }
.stSidebar .stButton { margin-bottom: 0.1rem !important; }
.stSidebar .stMarkdown { margin-bottom: 0.1rem !important; }
.stSidebar .element-container { margin-bottom: 0.1rem !important; }

/* Reduce sidebar heading sizes and spacing */
.stSidebar h1 { font-size: 1.1rem !important; margin: 0.1rem 0 !important; }
.stSidebar h2 { font-size: 1.0rem !important; margin: 0.1rem 0 !important; }
.stSidebar h3 { font-size: 0.95rem !important; margin: 0.1rem 0 !important; }
.stSidebar h4 { font-size: 0.9rem !important; margin: 0.1rem 0 !important; }
.stSidebar h5 { font-size: 0.85rem !important; margin: 0.1rem 0 !important; }

/* Compact expander and form elements */
.stSidebar .stExpander { margin: 0.1rem 0 !important; }
.stSidebar .streamlit-expanderHeader { padding: 0.2rem 0 !important; }
.stSidebar .streamlit-expanderContent { padding-top: 0.2rem !important; }

/* Reduce selectbox and input spacing */
.stSidebar .stSelectbox > label { margin-bottom: 0.1rem !important; }
.stSidebar .stTextInput > label { margin-bottom: 0.1rem !important; }
.stSidebar div[data-baseweb="select"] { margin-bottom: 0.2rem !important; }
.stSidebar div[data-baseweb="input"] { margin-bottom: 0.2rem !important; }

/* Target all sidebar widgets more aggressively */
.stSidebar .stVerticalBlock > .element-container { margin-bottom: 0.1rem !important; }
.stSidebar .stVerticalBlock { gap: 0.2rem !important; }
.stSidebar [data-testid="stVerticalBlock"] { gap: 0.2rem !important; }
.stSidebar [data-testid="element-container"] { margin-bottom: 0.1rem !important; }

/* Compact main content - reduce spacing in Actor Roles section */
.main h1 { margin: 0.5rem 0 !important; }
.main h2 { margin: 0.4rem 0 !important; }
.main h3 { margin: 0.3rem 0 !important; }
.main h4 { margin: 0.2rem 0 !important; }
.main p { margin: 0.2rem 0 !important; }
.main ul { margin: 0.2rem 0 !important; }
.main li { margin: 0.1rem 0 !important; }

/* Reduce spacing between markdown elements in main content */
.main .stMarkdown { margin-bottom: 0.3rem !important; }
.main .element-container { margin-bottom: 0.2rem !important; }

/* Compact spacing for role entry bullet points only - target list items */
div[data-testid="stMarkdownContainer"] ul { margin: 0.2rem 0 0.2rem 1.5rem !important; padding-left: 1.5rem !important; }
div[data-testid="stMarkdownContainer"] li { margin: 0.1rem 0 !important; line-height: 1.3 !important; }

/* Optional: hide Streamlit's default top menu and footer if you want max space */
header[data-testid="stHeader"] { height: 0px; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)



# Sidebar with connection and selectors
with st.sidebar:
    st.markdown("##### _I know I've seen that face before..._")
    st.markdown("### Cozy Mystery Lookup")
    
    # Neo4j connection settings (always shown)
    with st.expander("⚙️ Connection", expanded=False):
        st.text_input("URI", value=NEO4J_URI, key="uri")
        st.text_input("User", value=NEO4J_USER, key="user")
        st.text_input("Password", value=NEO4J_PASSWORD, type="password", key="pwd")
        st.text_input("Database", value=NEO4J_DB, key="db")
        if st.button("Reconnect"):
            os.environ["NEO4J_URI"] = st.session_state["uri"]
            os.environ["NEO4J_USER"] = st.session_state["user"]
            os.environ["NEO4J_PASSWORD"] = st.session_state["pwd"]
            os.environ["NEO4J_DATABASE"] = st.session_state["db"]
            st.cache_resource.clear()
            st.success("Driver reinitialized.")
            st.rerun()

    st.markdown("#### Select Episode")

    # Get current connection settings (prioritize UI input, then environment, then defaults)
    current_uri = st.session_state.get("uri", os.environ.get("NEO4J_URI", NEO4J_URI))
    current_user = st.session_state.get("user", os.environ.get("NEO4J_USER", NEO4J_USER))
    current_password = st.session_state.get("pwd", os.environ.get("NEO4J_PASSWORD", NEO4J_PASSWORD))
    current_db = st.session_state.get("db", os.environ.get("NEO4J_DATABASE", NEO4J_DB))

    # Get Neo4j driver
    driver = get_driver(current_uri, current_user, current_password)

    # Series selector
    with driver.session(database=current_db) as sess:
        series_rows = run_query(sess, CY_ALL_SERIES)

    if not series_rows:
        st.warning("No series found in database.")
        st.info("Import your data using the Neo4j queries from `neo4j_queries.md`")
        st.stop()

    s_labels = [f"{r['title']}" for r in series_rows]
    s_idx = st.selectbox("📺 Series:", range(len(series_rows)), format_func=lambda i: s_labels[i], key="series_idx")
    series = series_rows[s_idx]

    # Episode selector (depends on series)
    with driver.session(database=current_db) as sess:
        eps = run_query(sess, CY_EPISODES_IN_SERIES, {"t": series["tconst"]})

    if not eps:
        st.info("This series has no episodes in the dataset.")
        st.stop()

    # Season selector
    seasons = sorted({e.get("season") for e in eps if e.get("season") is not None})
    season_options = ["All"] + seasons if seasons else ["All"]
    selected_season = st.selectbox("🎬 Season:", season_options, key="season_idx")

    # Episode selector filtered by season
    filtered_eps = eps if selected_season == "All" else [e for e in eps if e.get("season") == selected_season]

    def ep_label(r):
        s = r.get("season")
        e = r.get("episode")
        se = f"S{s if s is not None else '?'}E{e if e is not None else '?'}"
        return f"{se}  ·  {r['title']}"

    e_idx = st.selectbox("🎬 Episode:", range(len(filtered_eps)), format_func=lambda i: ep_label(filtered_eps[i]), key="episode_idx")
    episode = filtered_eps[e_idx]

# Actor selector (depends on episode)
with driver.session(database=current_db) as sess:
    cast = run_query(sess, CY_CAST_FOR_EPISODE, {"et": episode["etconst"]})

# Actor selector (depends on episode)
with driver.session(database=current_db) as sess:
    cast = run_query(sess, CY_CAST_FOR_EPISODE, {"et": episode["etconst"]})

if not cast:
    st.info("No cast found for this episode.")
    st.stop()

# Two-column layout: actors on left, results on right
left_col, right_col = st.columns([1, 1])

with left_col:
    st.markdown("### 👥 Select Actor")
    
    # Create radio button options
    cast_options = []
    for i, r in enumerate(cast):
        roles = r["roles"] or []
        roles_txt = ", ".join(roles) if roles else "(uncredited/unknown)"
        cast_options.append(f"**{r['name']}**\n_{roles_txt}_")
    
    # Radio button selection
    selected_actor_idx = st.radio(
        "Choose an actor from this episode:",
        range(len(cast)),
        format_func=lambda i: cast_options[i],
        key="actor_radio"
    )
    
    actor = cast[selected_actor_idx]

# Query roles
with driver.session(database=current_db) as sess:
    data = run_query(sess, CY_ROLES_VIEW, {"n": actor["nconst"], "t": series["tconst"]})

if not data:
    st.warning("No role data found.")
    st.stop()

payload = data[0]
entries = payload.get("entries", [])

with right_col:
    st.markdown(f"### 🎭 Actor Roles: **{actor['name']}**")

    if not entries:
        st.write("No roles found.")
    else:
        from collections import defaultdict
        by_series = defaultdict(list)
        for row in entries:
            by_series[(row["seriesTconst"], row["seriesTitle"])].append(row)

        # Sort series alphabetically, but show current series first
        ordered = sorted(by_series.items(), key=lambda kv: (kv[0][1].lower()))
        ordered = sorted(ordered, key=lambda kv: 0 if kv[0][0] == series["tconst"] else 1)

        for (tconst, title), entries in ordered:
            st.markdown(f"#### {title}")
            for entry in entries:
                if entry["label"] == "Recurring":
                    st.markdown(f"- **{entry['character']}** — Recurring ({entry['count']} eps)")
                else:
                    epbadges = ", ".join([f"S{e.get('season')}E{e.get('episode')}" for e in (entry.get("sampleEpisodes") or [])])
                    st.markdown(f"- **{entry['character']}** — {epbadges if epbadges else 'Single/Pair'}")