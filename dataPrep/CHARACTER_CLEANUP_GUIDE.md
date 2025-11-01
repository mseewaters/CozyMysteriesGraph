# Character Name Cleanup Guide

## Overview

The character name cleanup utility solves two major data quality issues:

1. **Missing Character Names**: TMDb sometimes has empty character names where IMDb has the data
2. **Inconsistent Character Names**: Different variations of the same character across sources

## Features

### 1. Automatic Backfilling
- Finds missing character names in TMDb data by looking up the same actor in IMDb data
- Uses both `nconst` (IMDb person ID) and actor name matching
- Prioritizes most common character name for recurring actors

### 2. Fuzzy Matching
- Uses fuzzy string matching to find similar character names
- Handles variations like "Officer Fidel" vs "DS Fidel"
- Configurable similarity threshold (default: 80%)

### 3. LLM-Powered Normalization
- Uses GPT-4 to intelligently normalize character name variations
- Considers context like actor name and series
- Handles complex cases like rank changes, formal vs informal names

### 4. Manual Override System
- Supports manual character name mappings in JSON format
- Persistent storage of manual corrections
- Example mappings provided for common cases

## Usage

### Basic Usage
```bash
# Install dependencies
pip install -r requirements.txt

# Basic cleanup (requires OPENAI_API_KEY environment variable)
python character_name_cleanup.py \
  --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv \
  --imdb-cast GraphDB-files/out_cozy_actors.csv \
  --output GraphDB-files/cleaned_episode_cast.csv
```

### Advanced Options
```bash
# Disable LLM (faster, uses only fuzzy matching)
python character_name_cleanup.py \
  --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv \
  --imdb-cast GraphDB-files/out_cozy_actors.csv \
  --output GraphDB-files/cleaned_episode_cast.csv \
  --no-llm

# Adjust fuzzy matching sensitivity
python character_name_cleanup.py \
  --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv \
  --imdb-cast GraphDB-files/out_cozy_actors.csv \
  --output GraphDB-files/cleaned_episode_cast.csv \
  --fuzzy-threshold 85
```

## Setup Requirements

### Environment Variables
```bash
# Required for LLM features
OPENAI_API_KEY=your_openai_api_key_here
```

### Manual Mappings (Optional)
Create a `character_name_mappings.json` file for manual overrides:
```json
{
  "Officer Fidel": "DS Fidel Best",
  "Nicholas Barnaby": "Nick Barnaby",
  "Detective Inspector Barnaby": "DCI Tom Barnaby"
}
```

## Processing Logic

### Step 1: Missing Name Detection
- Identifies records with empty/generic character names in TMDb data
- Searches IMDb data for the same actor (by nconst and name)
- Backfills with most common character name for that actor

### Step 2: Fuzzy Matching
- Compares TMDb character names with IMDb variations for same actor
- Uses multiple fuzzy matching algorithms (ratio, partial, token-based)
- Finds potential matches above similarity threshold

### Step 3: LLM Normalization
- Groups similar character name variations
- Asks GPT-4 to provide canonical name considering context
- Applies normalization if LLM suggests a different name

### Step 4: Confidence Scoring
- Tracks the source and confidence of each change
- Adds `cleanup_notes` column explaining what was done
- Enables manual review of uncertain cases

## Output

The cleaned CSV includes all original columns plus:
- `cleanup_notes`: Explanation of what cleanup was performed
- Updated `characters` field with normalized names

## Example Improvements

| Original (TMDb) | IMDb Variation | LLM Normalized | Confidence |
|----------------|----------------|----------------|------------|
| "" | "DS Fidel Best" | "DS Fidel Best" | High (backfilled) |
| "Officer Fidel" | "DS Fidel Best" | "DS Fidel Best" | High (LLM) |
| "Nicholas Barnaby" | "Nick Barnaby" | "Nick Barnaby" | Medium (fuzzy + LLM) |
| "Detective Inspector Barnaby" | "DCI Tom Barnaby" | "DCI Tom Barnaby" | High (LLM) |

## Performance Notes

- **Fuzzy matching**: Fast, good for obvious similarities
- **LLM normalization**: Slower but more intelligent, requires API key and costs
- **Batch processing**: Processes 100 records at a time with progress updates
- **Caching**: Manual mappings are cached to avoid repeated LLM calls

## Integration with Existing Workflow

```bash
# 1. Generate TMDb data
python imdb_style_cast_from_tmdb.py --series tt0214950

# 2. Generate IMDb data  
python main.py

# 3. Clean up character names
python character_name_cleanup.py \
  --tmdb-cast GraphDB-files/imdb_style_episode_cast.csv \
  --imdb-cast GraphDB-files/out_cozy_actors.csv \
  --output GraphDB-files/cleaned_episode_cast.csv

# 4. Use cleaned data for Neo4j import
# (Use cleaned_episode_cast.csv instead of imdb_style_episode_cast.csv)
```

This creates a clean, consistent character name dataset that significantly improves the quality of your graph database relationships.