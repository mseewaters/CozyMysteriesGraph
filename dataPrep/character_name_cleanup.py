#!/usr/bin/env python3
"""
Character Name Cleanup Utility
------------------------------
Addresses two main issues:
1. Missing character names in TMDb - backfill from IMDb data
2. Inconsistent character names across sources - normalize using fuzzy matching + LLM

Features:
- Fuzzy matching to find similar character names
- LLM-based intelligent name normalization
- Confidence scoring for matches
- Manual review mode for uncertain cases
- Batch processing with progress tracking

Usage:
    python character_name_cleanup.py --tmdb-cast ../GraphDB-files/imdb_style_episode_cast.csv --imdb-cast ../GraphDB-files/out_cozy_actors.csv --output ../GraphDB-files/cleaned_episode_cast.csv
"""

import pandas as pd
import json
import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import re

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Fuzzy matching
try:
    from fuzzywuzzy import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    print("Warning: fuzzywuzzy not available. Install with: pip install fuzzywuzzy python-levenshtein")
    FUZZY_AVAILABLE = False

# LLM integration (OpenAI API)
try:
    import openai
    from openai import OpenAI
    LLM_AVAILABLE = True
    
    # Try to get API key (should now work with .env file loaded)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print(f"✓ OpenAI API key loaded (ends with: ...{OPENAI_API_KEY[-4:]})")
    else:
        openai_client = None
        print("Warning: OPENAI_API_KEY not found in environment variables or .env file. LLM features will be disabled.")
        print("Make sure your .env file contains: OPENAI_API_KEY=your_key_here")
except ImportError:
    print("Warning: openai not available. Install with: pip install openai")
    LLM_AVAILABLE = False
    openai_client = None


@dataclass
class CharacterMatch:
    """Represents a potential character name match"""
    tmdb_name: str
    imdb_name: str
    actor_name: str
    series_title: str
    fuzzy_score: int
    confidence: str  # 'high', 'medium', 'low'
    match_type: str  # 'exact', 'fuzzy', 'llm', 'manual'
    normalized_name: str


class CharacterNameCleaner:
    def __init__(self, use_llm: bool = True, fuzzy_threshold: int = 80):
        self.use_llm = use_llm and LLM_AVAILABLE and openai_client is not None
        self.fuzzy_threshold = fuzzy_threshold
        self.character_mappings: Dict[str, str] = {}
        self.manual_mappings: Dict[str, str] = {}
        self.llm_cache: Dict[str, str] = {}  # Cache LLM responses to avoid duplicate calls
        self.load_manual_mappings()
        
    def load_manual_mappings(self):
        """Load any existing manual character name mappings"""
        mappings_file = Path(__file__).parent / "character_name_mappings.json"
        if mappings_file.exists():
            try:
                with open(mappings_file, 'r', encoding='utf-8') as f:
                    self.manual_mappings = json.load(f)
                print(f"Loaded {len(self.manual_mappings)} manual character mappings")
            except Exception as e:
                print(f"Warning: Could not load manual mappings: {e}")
    
    def save_manual_mappings(self):
        """Save manual character name mappings for future use"""
        mappings_file = Path(__file__).parent / "character_name_mappings.json"
        try:
            with open(mappings_file, 'w', encoding='utf-8') as f:
                json.dump(self.manual_mappings, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.manual_mappings)} manual character mappings")
        except Exception as e:
            print(f"Warning: Could not save manual mappings: {e}")
    
    def analyze_title_normalization_candidates(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Analyze the dataset to find character names that could benefit from title normalization"""
        title_candidates = defaultdict(list)
        
        # Common abbreviations to look for
        abbreviations = ['DI', 'DCI', 'DS', 'DC', 'CI', 'PC', 'Dr', 'Prof', 'Lt', 'Capt', 'Sgt', 
                        'Mr', 'Mrs', 'Ms', 'Rev', 'Fr', 'Sr']
        
        for _, row in df.iterrows():
            characters = row.get('characters', '')
            actor_name = row.get('primaryName', '')
            
            # Clean and extract character name
            clean_char = self.clean_character_name(characters)
            if not clean_char:
                continue
            
            # Check for abbreviations that might need expansion
            for abbrev in abbreviations:
                if re.search(r'\b' + re.escape(abbrev) + r'\.?\b', clean_char, re.IGNORECASE):
                    title_candidates[f"Contains '{abbrev}'"].append(f"{clean_char} (Actor: {actor_name})")
        
        return dict(title_candidates)
    
    def clean_character_name(self, name: str) -> str:
        """Basic character name cleaning"""
        if not name or name in ['[]', '', 'null']:
            return ""
        
        # Remove JSON array brackets if present
        if name.startswith('[') and name.endswith(']'):
            try:
                parsed = json.loads(name)
                if isinstance(parsed, list) and len(parsed) > 0:
                    name = parsed[0]
                else:
                    return ""
            except json.JSONDecodeError:
                # Remove brackets manually
                name = name.strip('[]"')
        
        # Basic cleaning
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)  # Multiple spaces to single
        
        return name
    
    def get_title_variations(self, name: str) -> Set[str]:
        """Generate title variations for better fuzzy matching"""
        variations = {name}
        
        # Common title abbreviations and expansions
        title_mappings = {
            # Police/Detective titles
            'Detective Inspector': ['DI', 'Det. Inspector', 'Detective Insp.', 'Det Insp'],
            'Detective Chief Inspector': ['DCI', 'Det. Chief Inspector', 'Detective Ch. Inspector'],
            'Detective Superintendent': ['DSI', 'Det. Superintendent', 'Detective Supt.'],
            'Detective Sergeant': ['DS', 'Det. Sergeant', 'Detective Sgt.'],
            'Police Constable': ['PC', 'Constable', 'P.C.'],
            'Detective Constable': ['DC', 'Det. Constable', 'Detective Con.'],
            'Chief Inspector': ['CI', 'Ch. Inspector', 'Chief Insp.'],
            'Inspector': ['Insp.', 'Insp'],
            'Sergeant': ['Sgt', 'Sgt.', 'Sergt.'],
            
            # Medical titles
            'Doctor': ['Dr', 'Dr.', 'Doc'],
            'Professor': ['Prof', 'Prof.'],
            
            # Military titles
            'Lieutenant': ['Lt', 'Lt.', 'Lieut.'],
            'Captain': ['Capt', 'Capt.'],
            'Major': ['Maj', 'Maj.'],
            'Colonel': ['Col', 'Col.'],
            'General': ['Gen', 'Gen.'],
            
            # Civilian titles
            'Mister': ['Mr', 'Mr.'],
            'Missus': ['Mrs', 'Mrs.'],
            'Miss': ['Ms', 'Ms.'],
            'Reverend': ['Rev', 'Rev.'],
            'Father': ['Fr', 'Fr.'],
            'Sister': ['Sr', 'Sr.'],
            
            # Professional titles
            'Solicitor': ['Sol.'],
            'Barrister': ['Bar.'],
            'Judge': ['J.'],
            'Magistrate': ['Mag.'],
        }
        
        # Generate variations by replacing titles
        for full_title, abbreviations in title_mappings.items():
            # If name contains full title, add abbreviated versions
            if full_title.lower() in name.lower():
                base_name = re.sub(re.escape(full_title), '', name, flags=re.IGNORECASE).strip()
                for abbrev in abbreviations:
                    variations.add(f"{abbrev} {base_name}".strip())
                    variations.add(f"{base_name} {abbrev}".strip())  # Sometimes titles come after
            
            # If name contains abbreviation, add full version
            for abbrev in abbreviations:
                if abbrev.lower() in name.lower():
                    # Use word boundaries to avoid partial matches
                    pattern = r'\b' + re.escape(abbrev) + r'\b'
                    if re.search(pattern, name, re.IGNORECASE):
                        expanded = re.sub(pattern, full_title, name, flags=re.IGNORECASE)
                        variations.add(expanded.strip())
        
        # Handle common patterns
        # Remove/add periods from abbreviations
        no_periods = re.sub(r'\.', '', name)
        with_periods = re.sub(r'\b([A-Z])([A-Z])\b', r'\1.\2.', name)
        variations.add(no_periods)
        variations.add(with_periods)
        
        # Handle "The" prefix
        if name.lower().startswith('the '):
            variations.add(name[4:])  # Remove "The "
        else:
            variations.add(f"The {name}")  # Add "The "
        
        return variations
    
    def find_fuzzy_matches(self, tmdb_name: str, imdb_characters: List[str], threshold: int = None) -> List[Tuple[str, int]]:
        """Find fuzzy matches for a character name using title variations"""
        if not FUZZY_AVAILABLE or not tmdb_name or not imdb_characters:
            return []
        
        threshold = threshold or self.fuzzy_threshold
        matches = []
        
        # Generate variations for the TMDb name
        tmdb_variations = self.get_title_variations(tmdb_name)
        
        for imdb_name in imdb_characters:
            if not imdb_name:
                continue
            
            # Generate variations for the IMDb name too
            imdb_variations = self.get_title_variations(imdb_name)
            
            best_score = 0
            
            # Compare all variations against each other
            for tmdb_var in tmdb_variations:
                for imdb_var in imdb_variations:
                    # Try different fuzzy matching strategies
                    ratio = fuzz.ratio(tmdb_var.lower(), imdb_var.lower())
                    partial = fuzz.partial_ratio(tmdb_var.lower(), imdb_var.lower())
                    token_sort = fuzz.token_sort_ratio(tmdb_var.lower(), imdb_var.lower())
                    token_set = fuzz.token_set_ratio(tmdb_var.lower(), imdb_var.lower())
                    
                    # Use the highest score from this comparison
                    current_score = max(ratio, partial, token_sort, token_set)
                    best_score = max(best_score, current_score)
            
            if best_score >= threshold:
                matches.append((imdb_name, best_score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def handle_obvious_normalization(self, names: List[str]) -> Optional[str]:
        """Handle obvious formatting differences and title variations"""
        if not names or len(names) < 2:
            return None
        
        # Clean and prepare names for analysis
        cleaned_names = [name.strip() for name in names if name.strip()]
        if len(cleaned_names) < 2:
            return None
        
        # Check if names are just formatting differences
        normalized_set = set()
        for name in cleaned_names:
            # Normalize: lowercase, remove punctuation, remove extra spaces
            normalized = re.sub(r'[^\w\s]', '', name.lower()).strip()
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized_set.add(normalized)
        
        # If all names are identical after normalization (just formatting differences)
        if len(normalized_set) == 1:
            # Choose the "best" formatted version
            def score_name(name):
                score = 0
                # Prefer abbreviations over full titles
                abbreviations = ['DI', 'DCI', 'DS', 'DC', 'CI', 'PC', 'Dr', 'Prof', 'Lt', 'Capt', 'Sgt']
                for abbrev in abbreviations:
                    if re.search(r'\b' + re.escape(abbrev) + r'\.?\b', name, re.IGNORECASE):
                        score += 20  # Heavy bonus for abbreviations
                
                # Proper capitalization (each word starts with capital)
                words = name.split()
                if words and all(word[0].isupper() for word in words if word):
                    score += 10
                
                # Formal punctuation (periods after abbreviations)
                if '.' in name:
                    score += 5
                
                # Prefer shorter names (more concise) - reverse the length preference
                score += (10 - len(name.split()))  # Shorter gets higher score
                
                return score
            
            best_name = max(cleaned_names, key=score_name)
            return best_name
        
        # Check for title abbreviation/expansion matches
        # Group names by their core content (without titles)
        title_groups = defaultdict(list)
        
        for name in cleaned_names:
            # Extract the core name without common titles
            core_name = name
            title_prefixes = ['DI', 'DCI', 'DS', 'DC', 'CI', 'PC', 'Dr', 'Prof', 'Lt', 'Capt', 'Sgt',
                             'Detective Inspector', 'Detective Chief Inspector', 'Detective Sergeant',
                             'Detective Constable', 'Chief Inspector', 'Police Constable', 'Doctor',
                             'Professor', 'Lieutenant', 'Captain', 'Sergeant', 'Inspector', 'Mr', 'Mrs', 'Ms']
            
            for prefix in title_prefixes:
                pattern = r'\b' + re.escape(prefix) + r'\.?\s*'
                core_name = re.sub(pattern, '', core_name, flags=re.IGNORECASE).strip()
            
            # Remove "The" prefix too
            core_name = re.sub(r'^the\s+', '', core_name, flags=re.IGNORECASE).strip()
            
            if core_name:
                title_groups[core_name.lower()].append(name)
        
        # If we have one group with multiple title variations, pick the best one
        if len(title_groups) == 1:
            group_names = list(title_groups.values())[0]
            if len(group_names) > 1:
                # Prefer abbreviations over full titles
                def title_score(name):
                    score = 0
                    # Abbreviations get high scores
                    abbreviations = ['DI', 'DCI', 'DS', 'DC', 'CI', 'PC', 'Dr', 'Prof', 'Lt', 'Capt', 'Sgt']
                    for abbrev in abbreviations:
                        if re.search(r'\b' + re.escape(abbrev) + r'\.?\b', name, re.IGNORECASE):
                            score += 50
                    
                    # Proper case
                    if name[0].isupper():
                        score += 10
                    
                    # Length (more concise is better)
                    score += (50 - len(name))  # Shorter names get higher scores
                    
                    return score
                
                return max(group_names, key=title_score)
        
        return None
    
    def llm_normalize_character_names(self, names: List[str], actor_name: str = "", series_title: str = "") -> Optional[str]:
        """Use LLM to intelligently normalize character names with caching and batching optimization"""
        if not self.use_llm or not names:
            return None
        
        # Create cache key from sorted names (order shouldn't matter)
        cache_key = "|".join(sorted([name.lower().strip() for name in names if name]))
        
        # Check cache first
        if cache_key in self.llm_cache:
            return self.llm_cache[cache_key]
        
        # Pre-filtering: Handle obvious cases without LLM
        result = self.handle_obvious_normalization(names)
        if result:
            self.llm_cache[cache_key] = result
            return result
        
        # Prepare context for the LLM with title awareness
        names_text = ", ".join([f'"{name}"' for name in names if name])
        
        # Enhanced prompt with title normalization guidance
        prompt = f"""Normalize this character name from variants: {names_text}

Rules: 
- Prefer abbreviations over full titles (DI > Detective Inspector, Dr > Doctor)
- Use concise, standard abbreviations for titles
- Standardize police/military/professional title abbreviations
- Keep consistent capitalization

Output only the best normalized name:"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheapest model: ~$0.00015/1K tokens
                messages=[{"role": "user", "content": prompt}],
                max_tokens=25,  # Increased slightly for longer titles
                temperature=0,  # Reduced for more deterministic results
            )
            
            normalized_name = response.choices[0].message.content.strip().strip('"')
            
            # Cache the result
            self.llm_cache[cache_key] = normalized_name
            return normalized_name
        
        except Exception as e:
            print(f"Warning: LLM normalization failed: {e}")
            return None
    
    def process_character_cleanup(self, tmdb_df: pd.DataFrame, imdb_df: pd.DataFrame) -> pd.DataFrame:
        """Main processing function to clean up character names"""
        
        print("Starting character name cleanup...")
        print(f"TMDb records: {len(tmdb_df)}")
        print(f"IMDb records: {len(imdb_df)}")
        
        # Verify castType field is present in input data
        if 'castType' in tmdb_df.columns:
            print(f"✓ castType field detected in TMDb data")
            cast_type_values = tmdb_df['castType'].value_counts()
            print(f"  Cast type distribution: {dict(cast_type_values)}")
        else:
            print("⚠ Warning: castType field not found in TMDb data")
        
        # Create actor-to-characters mapping from IMDb data (episode-specific when possible)
        imdb_actor_chars = defaultdict(set)
        imdb_episode_chars = defaultdict(lambda: defaultdict(set))  # tconst -> nconst -> characters
        
        for _, row in imdb_df.iterrows():
            actor_name = row.get('primaryName', '')
            nconst = row.get('nconst', '')
            tconst = row.get('tconst', '')
            characters = row.get('characters', '')
            
            if characters and characters != '[]':
                try:
                    char_list = json.loads(characters) if isinstance(characters, str) else characters
                    if isinstance(char_list, list):
                        for char in char_list:
                            if char and char.strip():
                                cleaned_char = self.clean_character_name(char)
                                if cleaned_char:
                                    # Global actor-character mapping
                                    imdb_actor_chars[nconst].add(cleaned_char)
                                    if actor_name:
                                        imdb_actor_chars[actor_name.lower()].add(cleaned_char)
                                    
                                    # Episode-specific mapping
                                    if tconst:
                                        imdb_episode_chars[tconst][nconst].add(cleaned_char)
                except:
                    # Handle non-JSON format
                    cleaned = self.clean_character_name(characters)
                    if cleaned:
                        imdb_actor_chars[nconst].add(cleaned)
                        if actor_name:
                            imdb_actor_chars[actor_name.lower()].add(cleaned)
                        
                        # Episode-specific mapping
                        if tconst:
                            imdb_episode_chars[tconst][nconst].add(cleaned)
        
        # Process TMDb records
        results = []
        matches_found = 0
        llm_normalizations = 0
        obvious_normalizations = 0
        manual_mappings_applied = 0
        
        for idx, row in tmdb_df.iterrows():
            if idx % 100 == 0:
                print(f"Processing row {idx}/{len(tmdb_df)}")
            
            result_row = row.copy()
            tmdb_char = self.clean_character_name(row.get('characters', ''))
            actor_name = row.get('primaryName', '')
            nconst = row.get('nconst', '')
            tconst = row.get('tconst', '')  # Episode identifier for better matching
            
            # Initialize cleanup_notes if not present
            if 'cleanup_notes' not in result_row:
                result_row['cleanup_notes'] = ''
            
            # PRIORITY 0: Check manual mappings first (highest priority)
            if tmdb_char and tmdb_char in self.manual_mappings:
                manual_result = self.manual_mappings[tmdb_char]
                result_row['characters'] = f'["{manual_result}"]'
                result_row['cleanup_notes'] = f'Manual mapping: {tmdb_char} → {manual_result}'
                manual_mappings_applied += 1
                results.append(result_row)
                continue  # Skip all other processing for manually mapped characters
            
            # If TMDb character is empty or generic, try to backfill from IMDb
            if not tmdb_char or tmdb_char.lower() in ['unknown', 'uncredited', 'n/a', 'self']:
                possible_chars = set()
                lookup_source = ""
                
                # Priority 1: Episode-specific character data (most accurate)
                if tconst and nconst and tconst in imdb_episode_chars and nconst in imdb_episode_chars[tconst]:
                    possible_chars.update(imdb_episode_chars[tconst][nconst])
                    lookup_source = "episode-specific IMDb data"
                
                # Priority 2: Actor's global character data
                if not possible_chars:
                    if nconst and nconst in imdb_actor_chars:
                        possible_chars.update(imdb_actor_chars[nconst])
                        lookup_source = "IMDb actor data (nconst)"
                    
                    if not possible_chars and actor_name and actor_name.lower() in imdb_actor_chars:
                        possible_chars.update(imdb_actor_chars[actor_name.lower()])
                        lookup_source = "IMDb actor data (name match)"
                
                if possible_chars:
                    # Use the most common character name for this actor
                    char_counts = Counter(possible_chars)
                    best_char = char_counts.most_common(1)[0][0]
                    result_row['characters'] = f'["{best_char}"]'
                    result_row['cleanup_notes'] = f'Backfilled from {lookup_source} (actor: {actor_name})'
                    matches_found += 1
                    
                    # Set tmdb_char so we can proceed with normalization if there are variants
                    tmdb_char = best_char
                else:
                    result_row['cleanup_notes'] = f'No IMDb character found for {actor_name} (nconst: {nconst}, tconst: {tconst})'
            
            
            # Now check for normalization opportunities (both for original TMDb names and backfilled ones)
            if tmdb_char:  # Only proceed if we have a character name (original or backfilled)
                possible_variants = set()
                
                # Collect possible variants from IMDb (prioritize episode-specific data)
                if tconst and nconst and tconst in imdb_episode_chars and nconst in imdb_episode_chars[tconst]:
                    possible_variants.update(imdb_episode_chars[tconst][nconst])
                
                # Add global character data as additional variants
                if nconst and nconst in imdb_actor_chars:
                    possible_variants.update(imdb_actor_chars[nconst])
                if actor_name and actor_name.lower() in imdb_actor_chars:
                    possible_variants.update(imdb_actor_chars[actor_name.lower()])
                
                # Find fuzzy matches
                if possible_variants:
                    fuzzy_matches = self.find_fuzzy_matches(tmdb_char, list(possible_variants))
                    
                    if fuzzy_matches:
                        # Check if we should normalize
                        all_variants = [tmdb_char] + [match[0] for match in fuzzy_matches[:3]]
                        
                        # Check if any variant has a manual mapping (second priority)
                        manual_match = None
                        for variant in all_variants:
                            if variant in self.manual_mappings:
                                manual_match = self.manual_mappings[variant]
                                break
                        
                        if manual_match:
                            result_row['characters'] = f'["{manual_match}"]'
                            result_row['cleanup_notes'] = f'Manual mapping from variant: {variant} → {manual_match}'
                            manual_mappings_applied += 1
                        
                        # Use normalization if we have multiple similar names and no manual mapping
                        elif len(set(all_variants)) > 1:
                            # Try obvious normalization first
                            obvious_result = self.handle_obvious_normalization(all_variants)
                            if obvious_result and obvious_result != tmdb_char:
                                result_row['characters'] = f'["{obvious_result}"]'
                                result_row['cleanup_notes'] = f'Rule-based normalization: {", ".join(all_variants[:3])} → {obvious_result}'
                                obvious_normalizations += 1
                            elif self.use_llm:
                                # Quick pre-check: if differences are only case/punctuation, skip LLM
                                normalized_variants = [v.lower().replace(".", "").replace(",", "") for v in all_variants]
                                if len(set(normalized_variants)) == 1:
                                    if 'cleanup_notes' not in result_row or pd.isna(result_row.get('cleanup_notes')) or not result_row['cleanup_notes']:
                                        result_row['cleanup_notes'] = f'Variants differ only in case/punctuation: {", ".join(all_variants[:3])}'
                                else:
                                    series_title = ""  # Could extract from tconst if needed
                                    normalized = self.llm_normalize_character_names(all_variants, actor_name, series_title)
                                    
                                    if normalized:
                                        # Apply LLM result if it's different OR if it chose from available variants
                                        if normalized != tmdb_char or normalized in all_variants[1:]:
                                            result_row['characters'] = f'["{normalized}"]'
                                            existing_note = result_row.get('cleanup_notes', '')
                                            llm_note = f'LLM normalized from variants: {", ".join(all_variants[:3])} → {normalized}'
                                            result_row['cleanup_notes'] = f'{existing_note}; {llm_note}' if existing_note else llm_note
                                            llm_normalizations += 1
                                        else:
                                            if 'cleanup_notes' not in result_row or pd.isna(result_row.get('cleanup_notes')) or not result_row['cleanup_notes']:
                                                result_row['cleanup_notes'] = f'LLM confirmed original: {tmdb_char} (from variants: {", ".join(all_variants[:3])})'
                                    else:
                                        if 'cleanup_notes' not in result_row or pd.isna(result_row.get('cleanup_notes')) or not result_row['cleanup_notes']:
                                            result_row['cleanup_notes'] = f'LLM normalization failed (variants: {", ".join(all_variants[:3])})'
                        else:
                            # Use highest scoring fuzzy match if score is very high
                            best_match, score = fuzzy_matches[0]
                            if score >= 95 and best_match != tmdb_char:
                                result_row['characters'] = f'["{best_match}"]'
                                existing_note = result_row.get('cleanup_notes', '')
                                fuzzy_note = f'Fuzzy match (score: {score})'
                                result_row['cleanup_notes'] = f'{existing_note}; {fuzzy_note}' if existing_note else fuzzy_note
                                matches_found += 1
                            else:
                                if 'cleanup_notes' not in result_row or pd.isna(result_row.get('cleanup_notes')) or not result_row['cleanup_notes']:
                                    result_row['cleanup_notes'] = f'Fuzzy candidates found (best: {score})'
                    else:
                        if 'cleanup_notes' not in result_row or pd.isna(result_row.get('cleanup_notes')) or not result_row['cleanup_notes']:
                            result_row['cleanup_notes'] = 'No similar IMDb characters found'
                else:
                    if 'cleanup_notes' not in result_row or pd.isna(result_row.get('cleanup_notes')) or not result_row['cleanup_notes']:
                        result_row['cleanup_notes'] = 'No IMDb data for this actor'
            
            results.append(result_row)
        
        print(f"\nCleanup Summary:")
        print(f"- Records processed: {len(results)}")
        print(f"- Manual mappings applied: {manual_mappings_applied}")
        print(f"- Character names backfilled/corrected: {matches_found}")
        print(f"- Rule-based normalizations: {obvious_normalizations}")
        print(f"- LLM normalizations: {llm_normalizations}")
        print(f"- LLM cache hits: {len(self.llm_cache)} unique normalizations")
        if self.llm_cache:
            # Estimate cost savings from caching
            total_potential_calls = llm_normalizations + len([r for r in results if 'LLM confirmed' in r.get('cleanup_notes', '')])
            cache_savings = total_potential_calls - len(self.llm_cache)
            if cache_savings > 0:
                print(f"- LLM calls saved by caching: {cache_savings} (~${cache_savings * 0.0002:.4f} saved)")
            estimated_cost = len(self.llm_cache) * 0.0002  # Rough estimate for gpt-4o-mini
            print(f"- Estimated LLM cost: ~${estimated_cost:.4f}")
        
        # Create output DataFrame and verify castType field is preserved
        output_df = pd.DataFrame(results)
        
        if 'castType' in output_df.columns:
            print(f"✓ castType field preserved in output data")
            cast_type_values = output_df['castType'].value_counts()
            print(f"  Output cast type distribution: {dict(cast_type_values)}")
        else:
            print("⚠ Warning: castType field missing from output data")
        
        return output_df


def main():
    parser = argparse.ArgumentParser(description="Clean up character names in TMDb cast data")
    parser.add_argument("--tmdb-cast", required=True, help="Path to TMDb cast CSV file")
    parser.add_argument("--imdb-cast", required=True, help="Path to IMDb actors CSV file") 
    parser.add_argument("--output", required=True, help="Path for cleaned output CSV")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM normalization")
    parser.add_argument("--fuzzy-threshold", type=int, default=80, help="Fuzzy matching threshold (0-100)")
    parser.add_argument("--analyze-titles", action="store_true", help="Analyze and report title normalization candidates")
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading TMDb cast data from {args.tmdb_cast}")
    tmdb_df = pd.read_csv(args.tmdb_cast)
    
    print(f"Loading IMDb actors data from {args.imdb_cast}")
    imdb_df = pd.read_csv(args.imdb_cast)
    
    # Initialize cleaner
    cleaner = CharacterNameCleaner(
        use_llm=not args.no_llm,
        fuzzy_threshold=args.fuzzy_threshold
    )
    
    # Optional: Analyze title normalization candidates
    if args.analyze_titles:
        print("\n=== TITLE NORMALIZATION ANALYSIS ===")
        candidates = cleaner.analyze_title_normalization_candidates(tmdb_df)
        for category, examples in candidates.items():
            print(f"\n{category}:")
            for example in examples[:10]:  # Show first 10 examples
                print(f"  - {example}")
            if len(examples) > 10:
                print(f"  ... and {len(examples) - 10} more")
        print(f"\nTotal categories found: {len(candidates)}")
    
    # Process cleanup
    cleaned_df = cleaner.process_character_cleanup(tmdb_df, imdb_df)
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Save with proper CSV quoting to handle commas in text fields
    cleaned_df.to_csv(output_path, index=False, quoting=1, escapechar='\\')
    
    print(f"\nCleaned data saved to: {output_path}")
    
    # Save any manual mappings
    cleaner.save_manual_mappings()


if __name__ == "__main__":
    main()