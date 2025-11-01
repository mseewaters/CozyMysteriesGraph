# Cozy Mysteries Graph Database Project 🕵️‍♀️

A comprehensive data pipeline and graph database solution for analyzing cozy mystery TV series, their actors, episodes, and character relationships. This project demonstrates the power of graph databases for entertainment data analysis and provides tools for data extraction, cleaning, and visualization.

## 🎯 Project Overview

This project creates a Neo4j graph database containing detailed information about cozy mystery TV series including:
- **Series**: Show metadata and ratings
- **Episodes**: Individual episode details with seasons and ratings  
- **Actors**: Cast member information with birth/death years
- **Characters**: Character names and roles
- **Relationships**: Complex many-to-many relationships between actors, characters, episodes, and series

## 📊 Featured Series

- Midsomer Murders
- Father Brown  
- Death in Paradise
- Shakespeare & Hathaway: Private Investigators
- McDonald & Dodds
- Miss Fisher's Murder Mysteries
- Endeavour
- New Tricks
- Inspector Morse
- The Madame Blanc Mysteries
- Professor T
- Shetland
- Ludwig

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Processing     │    │     Output      │
│                 │    │                  │    │                 │
│ • IMDb Files    │───▶│ • Data Cleaning  │───▶│ • Neo4j Graph   │
│ • TMDb API      │    │ • Character      │    │ • CSV Exports   │
│ • Manual Data   │    │   Normalization  │    │ • Streamlit UI  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Neo4j Desktop or Neo4j AuraDB
- TMDb API Key (optional, for enhanced data)
- OpenAI API Key (optional, for character name cleanup)

### Installation

1. **Clone the repository**
   ```cmd
   git clone https://github.com/mseewaters/CozyMysteriesGraph.git
   cd CozyMysteriesGraph
   ```

2. **Set up virtual environment**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root with your API keys:
   ```ini
   TMDB_API_KEY=your_tmdb_api_key
   OPENAI_API_KEY=your_openai_api_key  
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```


### Basic Usage

1. **Download IMDb datasets** (place in `IMDB-files/` directory):
   - `title.basics.tsv`
   - `title.episode.tsv`
   - `title.principals.tsv`
   - `name.basics.tsv`
   - `title.ratings.tsv`

2. **Process IMDb data**:
   ```cmd
   python main.py
   ```

3. **Optional: Enhance with TMDb data**:
   ```cmd
   python imdb_style_cast_from_tmdb.py --series tt0214950 --max-rps 10
   ```

   Or process multiple series from file:
   ```cmd
   python imdb_style_cast_from_tmdb.py --file series_ids.txt --max-rps 10
   ```

4. **Optional: Clean character names**:

   With LLM (requires OpenAI API key):
   ```cmd
   python character_name_cleanup.py ^
     --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv ^
     --imdb-cast GraphDB-files/out_cozy_actors.csv ^
     --output GraphDB-files/cleaned_episode_cast.csv

   python character_name_cleanup.py --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv --imdb-cast GraphDB-files/out_cozy_actors.csv --output GraphDB-files/cleaned_episode_cast.csv
   ```

   Without LLM (fuzzy matching only):
   ```cmd
   python character_name_cleanup.py ^
     --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv ^
     --imdb-cast GraphDB-files/out_cozy_actors.csv ^
     --output GraphDB-files/cleaned_episode_cast.csv ^
     --no-llm
   ```

5. **Load data into Neo4j**:
   
   Import the CSV files into your Neo4j database. See `neo4j_import.md` for detailed Cypher import commands.
   
   Basic import example:
   ```cypher
   // Load Series
   LOAD CSV WITH HEADERS FROM 'file:///GraphDB-files/out_cozy_series.csv' AS row
   CREATE (s:Series {
     tconst: row.tconst,
     primaryTitle: row.primaryTitle,
     startYear: toInteger(row.startYear),
     genres: row.genres
   })
   
   // Load Episodes, Actors, and relationships...
   // See neo4j_import.md for complete import script
   ```

6. **Launch Streamlit interface**:
   ```cmd
   streamlit run streamlit_app.py
   ```

## 📁 Project Structure

```
CozyMysteriesGraph/
├── 📊 Data Processing
│   ├── main.py                          # IMDb data extraction and filtering
│   ├── imdb_style_cast_from_tmdb.py     # TMDb API integration with caching
│   └── character_name_cleanup.py        # AI-powered character name normalization
│
├── 🗃️ Data Storage  
│   ├── IMDB-files/                      # Raw IMDb TSV files
│   └── GraphDB-files/                   # Processed CSV files for Neo4j
│
├── 🖥️ User Interfaces
│   ├── streamlit_app.py                 # Neo4j-powered actor lookup
│   ├── graph_vs_relational_analysis.py # Database comparison tool
│   └── relational_actor_lookup.py       # SQL alternative implementation
│
├── 🛠️ Utilities & Demos
│   ├── demo_character_cleanup.py        # Character cleanup demonstration
│   ├── actor_clean.py                   # Actor data cleaning utilities
│   └── series_ids.txt                   # Series identifiers
│
├── 📚 Documentation
│   ├── README.md                        # This file
│   ├── CHARACTER_CLEANUP_GUIDE.md       # Character normalization guide
│   ├── Showcase.md                      # Project showcase
│   ├── neo4j_import.md                  # Neo4j import instructions
│   └── neo4j_queries.md                 # Sample Cypher queries
│
└── 📋 Configuration
    ├── requirements.txt                 # Python dependencies
    ├── .env                            # Environment variables (create from .env.example)
    └── character_name_mappings.json     # Manual character name overrides
```

## 🎛️ Core Components

### 1. Data Extraction (`main.py`)
- Interactive series selection using questionary
- IMDb dataset processing and filtering  
- Automatic CSV generation for selected series
- Outputs: `out_cozy_series.csv`, `out_cozy_episodes.csv`, `out_cozy_actors.csv`

### 2. TMDb Integration (`imdb_style_cast_from_tmdb.py`)
- Hybrid approach: IMDb + TMDb data
- 91.8% API call reduction through intelligent caching
- Synthetic ID generation for missing IMDb matches
- Cast type classification (regular vs guest stars)
- Rate limiting and retry logic

### 3. Character Name Cleanup (`character_name_cleanup.py`)
- **Fuzzy Matching**: Finds similar character names across sources
- **LLM Normalization**: GPT-4 powered intelligent name standardization
- **Backfilling**: Fills missing TMDb character names from IMDb data
- **Manual Overrides**: JSON-based manual corrections
- Handles cases like "Officer Fidel" → "DS Fidel Best"

### 4. Streamlit Interface (`streamlit_app.py`)
- Interactive actor role lookup
- Neo4j graph database integration
- Hierarchical navigation: Series → Season → Episode → Actor
- Real-time character role exploration

### 5. Database Comparison Tool (`graph_vs_relational_analysis.py`)
- Educational comparison of Graph vs Relational databases
- Multiple complexity levels with performance analysis
- Use case recommendations and trade-off analysis

## 🔧 Advanced Features

### Character Name Intelligence
The project includes sophisticated character name normalization:

```python
# Examples of automatic cleanup:
"" → "DCI Tom Barnaby"                    # Backfilled from IMDb
"Officer Fidel" → "DS Fidel Best"         # LLM normalization  
"Detective Inspector Barnaby" → "DCI John Barnaby"  # Title standardization
"Nicholas Barnaby" → "Nick Barnaby"       # Informal name preference
```

### API Optimization
TMDb integration includes advanced optimization:
- **Person Caching**: Reduces API calls by ~90%
- **Rate Limiting**: Configurable requests per second
- **Retry Logic**: Automatic retry with exponential backoff
- **Synthetic IDs**: Maintains data completeness for missing matches

### Graph Database Benefits
Demonstrates graph database advantages:
- **Complex Relationships**: Easily traverse actor-character-episode connections
- **Pattern Matching**: Find recurring characters, guest appearances, actor collaborations
- **Performance**: Fast traversals for relationship-heavy queries
- **Flexibility**: Schema-free evolution as data grows

## 📊 Sample Queries

### Find Recurring Characters
```cypher
MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WHERE s.primaryTitle = "Midsomer Murders"
WITH a, count(e) as episodes
WHERE episodes > 5  
RETURN a.primaryName, episodes
ORDER BY episodes DESC
```

### Actor Collaboration Networks
```cypher
MATCH (a1:Actor)-[:ACTED_IN]->(e:Episode)<-[:ACTED_IN]-(a2:Actor)
WHERE a1 <> a2
WITH a1, a2, count(e) as collaborations
WHERE collaborations > 2
RETURN a1.primaryName, a2.primaryName, collaborations
ORDER BY collaborations DESC
```

## 🛠️ Development

### Adding New Series
1. Add series to `cozy_titles` list in `main.py`
2. Run interactive selection process
3. Optionally enhance with TMDb data

### Extending Character Cleanup
1. Add patterns to `character_name_mappings.json`
2. Adjust fuzzy matching thresholds
3. Customize LLM prompts for domain-specific cases

### Database Schema Evolution
The graph schema supports easy extension:
- Add new node types (Directors, Writers)
- Create new relationships (DIRECTED, WROTE)  
- Add properties without schema migration

## 📈 Performance Metrics

- **API Optimization**: 91.8% reduction in TMDb person API calls
- **Data Coverage**: Handles missing IMDb matches with synthetic IDs
- **Character Quality**: Normalizes 80%+ of character name inconsistencies
- **Query Performance**: Sub-second response times for complex relationship queries

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **IMDb**: For comprehensive entertainment database
- **TMDb**: For API access and enhanced metadata
- **Neo4j**: For powerful graph database platform
- **OpenAI**: For intelligent character name normalization
- **Cozy Mystery Community**: For inspiring this analysis

## 📞 Support

- 📧 Issues: Use GitHub Issues for bug reports and feature requests
- 📖 Documentation: See `CHARACTER_CLEANUP_GUIDE.md` for detailed character cleanup instructions
- 🎯 Examples: Run `python demo_character_cleanup.py` for demonstrations

---

*Built with ❤️ for cozy mystery fans and data enthusiasts*