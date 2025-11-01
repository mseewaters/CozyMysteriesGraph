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
            "💡 Learnings & Next Steps"
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
     
elif page == "💡 Learnings & Next Steps":
    st.title("💡 Learnings & Next Steps")
    
    # Graph Fundamentals
    st.markdown("### 1️⃣ Graph Fundamentals")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        #### <u>Node vs Property Decisions</u>
        **Context determines the model:**
        - Cozy mysteries: Character as relationship property
        - Marvel/Dr. Who: Character as separate node entity
        - Same concept, different structures based on use case
        """, unsafe_allow_html=True)
        
        st.markdown("""
        #### <u>Cypher Language</u>
        **Much more intuitive than expected:**
        - Reads like English sentences
        - `(Actor)-[:ACTED_IN]->(Episode)` makes sense visually
        - No complex JOIN syntax to remember
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        #### <u>Neo4j Refresh Behavior</u>
        **Only adds/modifies, doesn't delete:**
        - Existing nodes and relationships persist
        - Need explicit DELETE commands for cleanup
        - Important for data pipeline design
        """, unsafe_allow_html=True)
        
        st.markdown("""
        #### <u>Graph Database Creation</u>
        **Simpler process than anticipated:**
        - LOAD CSV commands are straightforward
        - Visual feedback immediate
        - From zero to queries in minutes
        """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        #### <u>Data Prep for Neo4j</u>
        **Think relationships, not tables:**
        - Same CSV file can define nodes AND relationships
        - Focus on entity IDs for connections
        - Cleaner than expected conversion process
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        #### <u>Neo4j Online Hosting</u>
        **Auto-deletes after 1 month of inactivity:**
        - Important consideration for project continuity
        - Need backup strategy for long-term storage
        - Desktop version for development recommended
        """, unsafe_allow_html=True)
    
    st.markdown("---")
       
    # Data Engineering
    st.markdown("### 2️⃣ Data Engineering")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        #### <u>LLM Integration in Data Cleaning</u>
        **Actually practical and effective:**
        - Context-aware character name normalization
        - Reduced manual review by ~70%
        - Cost-effective for specific cleanup tasks
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        #### <u>Multiple Data Sources</u>
        **IMDB + TMDB complementary strengths:**
        - IMDB: Comprehensive cast data
        - TMDB: Cleaner metadata and character names
        - Combined dataset much richer than either alone
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Unexpected Discoveries
    st.markdown("### 3️⃣ Unexpected Discoveries")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        #### <u>British TV Actor Networks</u>
        **Smaller, more connected than expected:**
        - Same actors rotate through multiple mystery series
        - Guest stars become recurring faces across shows
        - British TV ecosystem is surprisingly tight-knit
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        #### <u>Hidden Patterns Emerge Naturally</u>
        **Graphs reveal unexpected connections:**
        - Actor career paths across series
        - Show interconnectedness through shared cast
        - Patterns I wasn't specifically looking for
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Next Steps
    st.markdown("## 🚀 Next Steps")
    
    st.markdown("""
    ### Where This Journey Leads
    
    **Immediate Applications:**
    - Apply graph thinking to our clinical trial data
    - Explore investigator networks and site relationships
    - Look for hidden patterns in therapy pathways
    
    **Team Learning:**
    - Share graph database concepts with the analytics team
    - Identify other relationship-heavy use cases in our work
    - Build comfort with visual data exploration tools
    """)
    
    st.markdown("---")
    
    st.markdown("### 🎬 Thank You!")
    st.markdown("*Questions? Let's explore some graphs together...*")
    