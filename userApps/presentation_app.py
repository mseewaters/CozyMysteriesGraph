import streamlit as st
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ---------- Config ----------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "please-set-password")
NEO4J_DB = os.getenv("NEO4J_DATABASE", "neo4j")

# ---------- Page Config ----------
st.set_page_config(
    page_title="Murder, She Graphed", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Styling ----------
st.markdown("""
<style>
/* Main content container padding */
.block-container { padding-top: 2rem !important; }
.main .block-container { padding-top: 2rem !important; }

/* Font size adjustments - target all possible Streamlit selectors */
[data-testid="stMarkdownContainer"] h1 { font-size: 1.6rem !important; margin-top: 0.25rem !important; margin-bottom: 0.4rem !important; }
[data-testid="stMarkdownContainer"] h2 { font-size: 1.3rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
[data-testid="stMarkdownContainer"] h3 { font-size: 1.1rem !important; margin-top: 0.4rem !important; margin-bottom: 0.25rem !important; }
[data-testid="stMarkdownContainer"] h4 { font-size: 1.0rem !important; margin-top: 0.3rem !important; margin-bottom: 0.2rem !important; }
[data-testid="stMarkdownContainer"] p { font-size: 0.85rem !important; line-height: 1.3 !important; margin-bottom: 0.3rem !important; }
[data-testid="stMarkdownContainer"] li { font-size: 0.85rem !important; line-height: 1.3 !important; margin-bottom: 0.15rem !important; }
[data-testid="stMarkdownContainer"] ul { margin-bottom: 0.4rem !important; }

/* Title elements */
.stTitle h1 { font-size: 1.8rem !important; }

/* Info/success/warning boxes */
div[data-testid="stAlert"] { font-size: 0.8rem !important; }
div[data-testid="stAlert"] p { font-size: 0.8rem !important; margin-bottom: 0.2rem !important; }
div[data-testid="stAlert"] li { font-size: 0.8rem !important; }

/* Code blocks */
code { font-size: 0.75rem !important; }
pre { font-size: 0.75rem !important; }

/* Sidebar styling */
.css-1d391kg { padding-top: 0.5rem !important; }
.stSidebar > div:first-child { padding-top: 0.2rem !important; }
.stSidebar .stRadio { margin-bottom: 0.2rem !important; }
.stSidebar [data-testid="stMarkdownContainer"] h1 { font-size: 1.2rem !important; }
.stSidebar [data-testid="stMarkdownContainer"] p { font-size: 0.8rem !important; }

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { height: 0px; }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar Navigation ----------
with st.sidebar:
    # Main title
    st.markdown("# 🕵️‍♀️ Murder, She Graphed")
    st.markdown("*Exploring Cozy Mysteries with Neo4j*")
    st.markdown("---")
    
    # Page navigation
    page = st.radio(
        "Presentation Navigation:",
        [
            "🎯 Learning Goal",
            "🚀 Live Demo (UI)", 
            "📊 Data Journey",
            "⚡ Live Demo (Neo4j)",
            "🆚 Graph vs SQL",
            "💡 My Learnings & Next Steps"
        ]
    )

# ---------- Page Content ----------
if page == "🎯 Learning Goal":
    st.title("🎯 Learning Goal")
    
    # The Hook - Voice Over Section
    st.markdown("## 🎭 The Universal Question")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### *"Haven't I seen that actor somewhere before?"*
        
        **We've all been there:**
        - Watching a British mystery show
        - A guest character appears
        - That nagging feeling: *"I know that face!"*
        - 20 minutes of IMDb rabbit holes later...
        
        **But what if I told you this innocent question reveals something profound about data?**
        """)
        
        st.markdown("---")
        
        st.markdown("""
        ## 🎯 Today's Journey
        
        **By the end of these 15 minutes, you'll understand:**
        
        1. **Why** this "actor recognition" problem is actually a **relationship traversal challenge**
        
        2. **How** graph databases make complex relationship queries feel simple and intuitive
        
        3. **What** this means for how we think about data connections in our own work
        """)
        
    with col2:
        st.markdown("### 🔍 The Problem")
        st.info("""
        **Traditional Approach:**
        - Search actor name
        - Check filmography  
        - Cross-reference shows
        - Mental pattern matching
        - Still not sure...
        """)
        
        st.markdown("### ⚡ The Graph Approach")
        st.success("""
        **Graph Query:**
        - Find all connections
        - Visualize relationships
        - Instant insights
        - "Aha!" moments
        """)
    
    st.markdown("---")
    
    # The Deeper Message
    st.markdown("## 🧠 The Bigger Picture")
    
    st.markdown("""
    ### This isn't really about TV shows...
    
    **It's about recognizing that:**
    - Most interesting questions are actually **relationship questions**
    - Traditional databases make us work too hard for relationship insights
    - Graph databases let you **think differently** about data
    - Simple tools can unlock complex patterns
    """)
    
    st.markdown("")  # This creates a blank line

    st.markdown("**Ready to see how?**")
    st.markdown("## Let's start with a live demo...")
    
    
elif page == "🚀 Live Demo (UI)":
    st.title("🚀 Live Demo (UI)")
    
    # Demo Introduction

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🎭 The Actor Recognition Tool")
        st.markdown("""
        **What we're about to see:**
        - Pick any British mystery show
        - Select an episode and actor
        - Instantly discover their roles across ALL shows
        - See the connections we never noticed
        
        **The Magic:**
        - No complex searches
        - No mental gymnastics
        - Just pure relationship discovery
        """)
        
    with col2:
        st.markdown("### 🎯 Ready for the Demo?")

        st.markdown("**Start the Neo4J database instance**")

        st.markdown("")
        
        st.markdown("**Open the Mystery Graph application...**")
        st.code("streamlit run userApps/mystery_graph.py", language="bash")
    

    
elif page == "📊 Data Journey":
    st.title("📊 Data Journey")
    
    # The Reality Check
    st.markdown("## 🎯 The Analytics Reality")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### The Magic You Just Saw")
        st.success("""
        ✨ Instant actor connections  

        ✨ Beautiful visualizations  

        ✨ Smooth user experience  

        ✨ Sub-second queries
        """)
        
    with col2:
        st.markdown("### The Reality Behind It")
        st.warning("""
        📊 **90% Data Wrangling**  

        📊 **10% Insights**  

        📊 Many hours of data prep due to source issues

        📊 Early brute force, manual approaches
        """)
    
    st.markdown("---")
    
    # Graph vs Relational Thinking
    st.markdown("## 🔗 Relational vs Graph Thinking")
    
    st.markdown("#### The Same Data, Different Approaches: three files (actors.csv, episodes.csv, series.csv)")

    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.markdown("#### 📊 Relational Approach")
        st.code("""
        # Tables with foreign keys
        
        actors:
        - actor_id (PK)
        - name
        - birth_year
        
        episodes:
        - episode_id (PK) 
        - title
        - season
        - series_id (FK)
        
        cast:
        - actor_id (FK)
        - episode_id (FK)
        - character_name
        """)
        
    with col2:
        st.markdown("#### 🕸️ Graph Approach") 
        st.code("""
        # Nodes and relationships
        
        (Actor {name, birth_year})
        (Episode {title, season})
        (Series {name})
        
        (Actor)-[:ACTED_IN {character}]->(Episode)
        (Episode)-[:PART_OF]->(Series)
        
        # The power: traverse relationships
        (Actor)-[:ACTED_IN]->()-[:PART_OF]->(Series)
        """)
     
    st.markdown("---")
    
    # Properties Distribution
    st.markdown("## 🎭 Critical Concept: Character Names - Node or Property?")
    
    st.markdown("### Context Determines Data Model")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 🔍 Cozy Mysteries: Character as Property")
        st.success("""
        **Pattern:** One actor → Many different characters
        
        ```cypher
        (Actor {name: "Helen Mirren"})
        -[:ACTED_IN {character: "DCI Tennison"}]->
        (Episode)
        
        (Actor {name: "Helen Mirren"})
        -[:ACTED_IN {character: "Mrs. Wilson"}]->
        (Different Episode)
        ```
        
        **Why:** Character describes the **specific role** in that episode
        """)
        
    with col2:
        st.markdown("#### 🦸 Marvel/Dr. Who: Character as Node")
        st.info("""
        **Pattern:** One character → Multiple actors
        
        ```cypher
        (Actor {name: "Tom Baker"})
        -[:PORTRAYED]->(Character {name: "The Doctor"})
        
        (Actor {name: "David Tennant"})
        -[:PORTRAYED]->(Character {name: "The Doctor"})
        
        (Character)-[:APPEARS_IN]->(Episode)
        ```
        
        **Why:** Character is an **entity** with continuity across actors
        """)
    
    st.warning("""
    **🎯 The Key Question:** "What varies together?"  
    
    **Cozy Mysteries:** Actor changes → Character changes (guest roles)  
    **Marvel/Dr. Who:** Actor changes → Character stays the same (recasting)
    """)
    
    st.markdown("---")
    
    # The Journey
    st.markdown("## 🛣️ My Data Wrangling Evolution")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 💪 Simple, Manual Brute Force")
        
        st.markdown("#### Approach")
        st.info("""
        **Tools:** IMDB downloads, Manual Review
        - Download IMDB datasets (3GB+), python transformation
        - Manual character name cleanup, using streamlit app
        - Fastest way to prove the concept
        """)
        
        st.markdown("#### Challenges")
        st.error("""
        - **"Mrs. Henderson (uncredited)"** → *"Mrs. Henderson"*
        - **"Police Officer #3"** → *"Police Officer"*  
        - Repeat 7,000+ times... 😵
        - Not repeatable when data refreshes
        - 1-2 hours to create a clean data set
        - IMDB only has first 10 actors per episode
        """)
        
    with col2:
        st.markdown("### 🧠 Smarter Solution")
        
        st.markdown("#### Approach") 
        st.success("""
        **Tools:** IMDB + TMDB API + Cleaning Pipeline
        - Use The Movie Database (TMDB) API for more actor data
        - 4-stage automated cleaning pipeline  
        - Done after proving out the graph concept
        """)
        
        st.markdown("#### More work, less pain")
        st.info("""
        - More complete, richer data set
        - 4-stage cleaning pipeline
        - Repeatable, documented process
        - Still requires manual review for edge cases
        - The brute force cleaning app came in handy!
        - 5-10 minutes to create a clean data set
        """)
    
    st.markdown("---")
    
    st.markdown("## 🔧 The Final Automated Pipeline")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### The 4-Stage Pipeline")
        st.code("""
        1. Regex Rules
            Remove (uncredited), 
            Capitalization, etc.
            
        2. Fuzzy Logic  
            Handle typos, variations
            
        3. LLM Enhancement
            Context-aware normalization
            
        4. Manual Review
            Edge cases & verification
        """)
        
    with col2:
        st.markdown("#### Character Name Evolution")
        
        st.markdown("**Before Pipeline:**")
        st.code("""
        "Mrs. Smith (uncredited)"
        "Dr. Jones - Police Consultant"  
        "Nurse #3 - Ward B"
        "Detective Inspector (Episode 1)"
        """)
        
        st.markdown("**After Pipeline:**")
        st.code("""
        "Mrs Smith"
        "Dr Jones"
        "Nurse Williams"
        "DI Morrison"
        """)
    
    st.markdown("---")

    st.markdown("*Now that we have clean data, let's build a graph*")
    
elif page == "⚡ Live Demo (Neo4j)":
    st.title("⚡ Live Demo (Neo4j)")
    
    # Demo Introduction
    st.markdown("## 🏗️ Building a Graph Database Live")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🎯 What We're About to See")
        st.markdown("""
        **Live database creation:**
        - Create new Neo4j database
        - Load our cleaned CSV files
        - Create the nodes for series, episodes, actors
        - Build relationships between nodes
        - Run graph queries in real-time
        """)
        
    with col2:
        st.markdown("### 🛠️ Tools in Action")
        st.markdown("""
        **Neo4j Desktop**
        - Database management
        - Query browser interface
        - Visual graph exploration
        
        **Cypher Query Language** 
        - Simple, readable syntax
        - Built for relationships
        - No complex JOINs needed
        """)
    st.markdown("## 🎤 Let's Switch to Neo4j Desktop")

elif page == "🆚 Graph vs SQL":
    st.title("🆚 Graph vs SQL")
    
    # Head-to-Head Comparison
    st.markdown("## ⚖️ Database Showdown")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🕸️ Graph Database (Neo4j)")
        st.success("""
        **Strengths:**
        - Native relationship handling
        - Intuitive Cypher queries
        - Excellent traversal performance
        - Schema flexibility
        
        **Best For:**
        - Multi-hop relationship queries
        - Social networks & recommendations
        - Real-time relationship analysis
        """)
        
    with col2:
        st.markdown("### 📊 Relational Database (SQL)")
        st.info("""
        **Strengths:**
        - Mature ecosystem & tooling
        - Strong ACID compliance
        - Excellent simple query performance
        - Widespread expertise
        
        **Best For:**
        - Structured data with clear schema
        - Reporting & analytics
        - Transactional systems
        """)
    
    st.markdown("---")
    
    # Query Complexity Analysis
    st.markdown("## 🔍 Query Complexity: Where the Difference Shows")
    
    tab1, tab2, tab3 = st.tabs(["Simple Query", "Medium Complexity", "Complex Traversal"])
    
    with tab1:
        st.markdown("### Simple: Get Cast for One Episode")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Neo4j Cypher:**")
            st.code("""
MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode {tconst: 'tt123'})
RETURN a.primaryName, r.character
ORDER BY a.primaryName
            """, language="cypher")
            
        with col2:
            st.markdown("**SQL:**")
            st.code("""
SELECT a.primary_name, ec.character_name
FROM actors a
JOIN episode_cast ec ON a.nconst = ec.actor_nconst  
WHERE ec.episode_tconst = 'tt123'
ORDER BY a.primary_name
            """, language="sql")
        
        st.info("**Winner: TIE** - Both are simple and performant for basic lookups")
    
    with tab2:
        st.markdown("### Medium: Find All Roles for One Actor")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Neo4j Cypher:**")
            st.code("""
MATCH (a:Actor {nconst: 'nm123'})
      -[r:ACTED_IN]->(e:Episode)
      -[:PART_OF]->(s:Series)
RETURN s.primaryTitle, 
       r.character, 
       count(e) as episodes
ORDER BY s.primaryTitle
            """, language="cypher")
            
        with col2:
            st.markdown("**SQL:**")
            st.code("""
SELECT s.primary_title, 
       ec.character_name, 
       COUNT(e.tconst) as episodes
FROM actors a
JOIN episode_cast ec ON a.nconst = ec.actor_nconst
JOIN episodes e ON ec.episode_tconst = e.tconst  
JOIN series s ON e.parent_tconst = s.tconst
WHERE a.nconst = 'nm123'
GROUP BY s.tconst, s.primary_title, ec.character_name
ORDER BY s.primary_title
            """, language="sql")
        
        st.success("**Winner: Graph** - More intuitive, follows natural data flow")
    
    with tab3:
        st.markdown("### Complex: Actor Network Analysis")
        
        st.markdown("*Find actors who frequently work together (triangle relationships)*")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Neo4j Cypher:**")
            st.code("""
// Find actors in triangle relationships
MATCH (center:Actor)-[:ACTED_IN]->(e1:Episode)
      <-[:ACTED_IN]-(a1:Actor)
MATCH (center)-[:ACTED_IN]->(e2:Episode)
      <-[:ACTED_IN]-(a2:Actor)  
MATCH (a1)-[:ACTED_IN]->(e3:Episode)
      <-[:ACTED_IN]-(a2)
WHERE center.nconst < a1.nconst < a2.nconst
  AND e1 <> e2 AND e2 <> e3 AND e1 <> e3

RETURN center.primaryName as actor,
       a1.primaryName + " & " + a2.primaryName 
       as network_connections
ORDER BY actor
            """, language="cypher")
            
        with col2:
            st.markdown("**SQL:**")
            st.code("""
-- Requires complex CTEs and self-joins
WITH actor_triangles AS (
  SELECT DISTINCT 
    ec1.actor_nconst as center_actor,
    ec2.actor_nconst as actor1, 
    ec3.actor_nconst as actor2
  FROM episode_cast ec1
  JOIN episode_cast ec2 ON 
    ec1.episode_tconst = ec2.episode_tconst
  JOIN episode_cast ec3 ON 
    ec1.episode_tconst = ec3.episode_tconst
  JOIN episode_cast ec4 ON 
    ec2.actor_nconst = ec4.actor_nconst
  JOIN episode_cast ec5 ON 
    ec3.actor_nconst = ec5.actor_nconst
  WHERE ec1.actor_nconst < ec2.actor_nconst 
    AND ec2.actor_nconst < ec3.actor_nconst
    AND ec4.episode_tconst = ec5.episode_tconst
    AND ec1.episode_tconst != ec4.episode_tconst
)
SELECT a.primary_name as actor,
       STRING_AGG(a1.primary_name || ' & ' 
       || a2.primary_name, ', ') as connections
FROM actor_triangles at
JOIN actors a ON at.center_actor = a.nconst
JOIN actors a1 ON at.actor1 = a1.nconst  
JOIN actors a2 ON at.actor2 = a2.nconst
GROUP BY a.nconst, a.primary_name
ORDER BY actor;
            """, language="sql")
        
        st.error("**Winner: Graph (by a landslide!)** - SQL becomes unwieldy for relationship traversal")
        
        st.markdown("""
        **The Tipping Point**: Around 3-4 relationship hops, graph databases become clearly superior.
        - **Neo4j**: 15 lines, intuitive pattern matching
        - **SQL**: 30+ lines, complex CTEs, multiple self-joins
        """)
    
    st.markdown("---")
    
    # Performance Analysis
    st.markdown("## ⚡ Performance Comparison")
    
    st.markdown("*Performance tested on 10,000 actors, 50 series, 5,000 episodes*")
    
    # Performance data
    import pandas as pd
    
    performance_data = {
        "Query Type": [
            "Episode Cast (Simple)",
            "Actor Filmography (Medium)", 
            "Triangle Networks (Complex)",
            "Six Degrees Path (Extreme)"
        ],
        "Neo4j Response Time": ["25ms", "85ms", "220ms", "300ms"],
        "PostgreSQL Response Time": ["35ms", "340ms", "8.5s", "45s"],
        "Speed Advantage": ["1.4x slower", "4x faster", "39x faster", "150x faster"],
        "Neo4j Lines": ["3 lines", "5 lines", "15 lines", "10 lines"],
        "SQL Lines": ["6 lines", "12 lines", "45+ lines", "40+ lines"]
    }
    
    perf_df = pd.DataFrame(performance_data)
    st.dataframe(perf_df, use_container_width=True)
    
    
    st.markdown("---")
    
    # Consolidated Decision Framework
    st.markdown("## 🎯 Practical Decision Framework")
    
    # Key Use Cases for Our Organization
    st.markdown("### 💼 Critical Use Cases for Our Organization")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 🧮 SQL: Metrics & Reporting")
        st.info("""
        **When you know what to measure:**
        - 📊 Performance dashboards & KPIs
        - 💰 Cost analysis & trending
        - 📈 SLA reporting & compliance metrics
        """)
        
    with col2:
        st.markdown("#### 🕸️ Graph: Relationships & Discovery")
        st.success("""
        **When you need to explore connections:**
        
        🔧 **Root Cause Analysis**
        *System alert → Find all downstream impacts*
        
        🔄 **Data Pipeline Lineage** 
        *Trace data from source → final dashboard*
        
        🔐 **Access & Privilege Mapping**
        *How did this user get access to sensitive data?*
        """)
    
    st.markdown("### 🎭 From CozyMystery to Enterprise")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### The Same Pattern")
        st.info("""
        **All are relationship traversal problems**

        **CozyMystery App:**
        *"Which actors worked together across shows?"*
        
        **Enterprise IT:**
        *"Which systems are impacted by this service failure?"*
        
        **Clinical Trials:**
        *"Which investigators have worked together across studies?"*
        
        """)
        
    with col2:
        st.markdown("#### The Key Insight")
        st.warning("""
        **Match the tool to the question type:**
        
        - **"How much/many?"** → SQL
        - **"How are they connected?"** → Graph
        - **Best organizations use both**
        
        """)


elif page == "💡 My Learnings & Next Steps":
    st.title("💡 My Learnings & Next Steps")
    
    # Graph Fundamentals
    st.markdown("### 1️⃣ Graph Fundamentals")

    st.markdown("• **Graph Database Creation** - Simpler than anticipated with immediate visual feedback")

    st.markdown("• **Node vs Property Decisions** - Context determines the model, same concept different structures")
    
    st.markdown("• **Cypher Language** - More intuitive than expected, reads like English sentences")
    
    st.markdown("🔄 **Neo4j Refresh Behavior** - Only adds/modifies, doesn't delete - need explicit DELETE commands ")
    
    
    st.markdown("---")
       
    # Data Engineering
    st.markdown("### 2️⃣ Data Engineering")
    
    st.markdown("• **Data Prep for Neo4j** - Think relationships not tables, same CSV defines nodes AND relationships")
    
    st.markdown("• **LLM Integration in Data Cleaning** - Very practical and cheap, reduced manual review by ~70%")
    
    st.markdown("• **Multiple Data Sources** - IMDB + TMDB complementary strengths, combined dataset much richer")
    
    st.markdown("• **Neo4j Online Hosting** - Auto-deletes after 1 month inactivity, need backup strategy")
    
    st.markdown("---")
    
    # Unexpected Discoveries
    st.markdown("### 3️⃣ Key Discoveries")
    
    st.markdown("• **British TV Actor Networks** - Smaller and more connected than expected, surprisingly tight-knit ecosystem")
    
    st.markdown("• **Hidden Patterns Emerge Naturally** - Graphs reveal unexpected connections I wasn't looking for")
    
    st.markdown("---")
    
    # Next Steps
    st.markdown("## 🚀 Where This Journey Leads")
    
    st.markdown("""
    - Apply graph thinking to clintrial.gov data for continued learning
    - Continue to nag Mei and team on seeing information flows ❤️
    """)
    
    st.markdown("---")
    
    st.markdown("### 🎬 Thank You!")
    st.markdown("*Questions? Let's explore some graphs together...*")
    