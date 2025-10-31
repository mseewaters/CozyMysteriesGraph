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
.block-container { padding-top: 0.75rem !important; }
.main .block-container { padding-top: 0.75rem !important; }        /* newer */
.stMainBlockContainer { padding-top: 0.75rem !important; }         /* fallback */

/* Reduce title spacing (h1) or hide it and render your own smaller label */
h1 { margin-top: 0.25rem !important; margin-bottom: 0.5rem !important; }

/* Optional: hide Streamlit’s default top menu and footer if you want max space */
header[data-testid="stHeader"] { height: 0px; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<style>h3 {font-size: 18px !important;}</style>",
    unsafe_allow_html=True
)

st.markdown(
    "<style>h4 {font-size: 18px !important;}</style>",
    unsafe_allow_html=True
)

st.markdown(
    "<style>h5 {font-size: 14px !important;}</style>",
    unsafe_allow_html=True
)

# Two-pane layout: left for picks, right for results
left, space, right = st.columns([1,0.1,2])

with st.sidebar:
    st.subheader("Neo4j connection")
    st.text_input("NEO4J_URI", value=NEO4J_URI, key="uri")

    st.text_input("NEO4J_USER", value=NEO4J_USER, key="user")
    st.text_input("NEO4J_PASSWORD", value=NEO4J_PASSWORD, type="password", key="pwd")
    if st.button("Reconnect"):
        os.environ["NEO4J_URI"] = st.session_state["uri"]
        os.environ["NEO4J_USER"] = st.session_state["user"]
        os.environ["NEO4J_PASSWORD"] = st.session_state["pwd"]
        os.environ["NEO4J_DATABASE"] = st.session_state["db"]
        st.cache_resource.clear()
        st.success("Driver reinitialized.")

driver = get_driver(os.environ.get("NEO4J_URI", NEO4J_URI),
                    os.environ.get("NEO4J_USER", NEO4J_USER),
                    os.environ.get("NEO4J_PASSWORD", NEO4J_PASSWORD))
NEO4J_DB = os.environ.get("NEO4J_DATABASE", NEO4J_DB)

with left:
    st.markdown("<h4>CozyMystery Actor Lookup</h4>", unsafe_allow_html=True)

    # Series selector
    with driver.session(database=NEO4J_DB) as sess:
        series_rows = run_query(sess, CY_ALL_SERIES)

    if not series_rows:
        st.warning("No series found. Is the database correct?")
        st.stop()

    s_labels = [f"{r['title']}" for r in series_rows]
    s_idx = st.selectbox("Series:", range(len(series_rows)), format_func=lambda i: s_labels[i], key="series_idx")
    series = series_rows[s_idx]

    # Episode selector (depends on series)
    with driver.session(database=NEO4J_DB) as sess:
        eps = run_query(sess, CY_EPISODES_IN_SERIES, {"t": series["tconst"]})

    if not eps:
        st.info("This series has no episodes in the dataset.")
        st.stop()

    # Season selector
    seasons = sorted({e.get("season") for e in eps if e.get("season") is not None})
    season_options = ["All"] + seasons if seasons else ["All"]
    selected_season = st.selectbox("Season:", season_options, key="season_idx")

    # Episode selector filtered by season
    filtered_eps = eps if selected_season == "All" else [e for e in eps if e.get("season") == selected_season]

    def ep_label(r):
        s = r.get("season")
        e = r.get("episode")
        se = f"S{s if s is not None else '?'}E{e if e is not None else '?'}"
        return f"{se}  ·  {r['title']}"

    e_idx = st.selectbox("Episode:", range(len(filtered_eps)), format_func=lambda i: ep_label(filtered_eps[i]), key="episode_idx")
    episode = filtered_eps[e_idx]

    # Actor selector (depends on episode)
    with driver.session(database=NEO4J_DB) as sess:
        cast = run_query(sess, CY_CAST_FOR_EPISODE, {"et": episode["etconst"]})

    if not cast:
        st.info("No cast found for this episode.")
        st.stop()

    cast_labels = []
    for r in cast:
        roles = r["roles"] or []
        roles_txt = ", ".join(roles) if roles else "(uncredited/unknown)"
        cast_labels.append(f"{r['name']} — {roles_txt}")

    a_idx = st.selectbox("Actor:", range(len(cast)), format_func=lambda i: cast_labels[i], key="actor_idx")
    actor = cast[a_idx]

# Query roles
with driver.session(database=NEO4J_DB) as sess:
    data = run_query(sess, CY_ROLES_VIEW, {"n": actor["nconst"], "t": series["tconst"]})

if not data:
    st.warning("No role data found.")
    st.stop()

payload = data[0]
entries = payload.get("entries", [])

with right:
    st.markdown(f"#### Roles for **{actor['name']}**")

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

        space2, right2 = st.columns([0.1,2]) 

        with right2:
            for (tconst, title), entries in ordered:
                st.markdown(f"##### {title}")
                for entry in entries:
                    if entry["label"] == "Recurring":
                        st.markdown(f"- **{entry['character']}** — Recurring ({entry['count']} eps)")
                    else:
                        epbadges = ", ".join([f"S{e.get('season')}E{e.get('episode')}" for e in (entry.get("sampleEpisodes") or [])])
                        st.markdown(f"- **{entry['character']}** — {epbadges if epbadges else 'Single/Pair'}")