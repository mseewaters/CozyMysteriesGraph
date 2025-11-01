"""
Script to add castType information to existing Neo4j ACTED_IN relationships
using the cleaned_episode_cast.csv file.
"""

import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ---------- Config ----------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "please-set-password")
NEO4J_DB = os.getenv("NEO4J_DATABASE", "neo4j")

def update_cast_types():
    """Update Neo4j relationships with castType information"""
    
    print("Loading cleaned episode cast data...")
    try:
        df = pd.read_csv("GraphDB-files/cleaned_episode_cast.csv")
        print(f"Loaded {len(df)} records from cleaned_episode_cast.csv")
        
        # Show cast type distribution
        cast_type_counts = df['castType'].value_counts()
        print(f"Cast type distribution: {dict(cast_type_counts)}")
        
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return False
    
    print(f"\nConnecting to Neo4j at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session(database=NEO4J_DB) as session:
            # Check if any relationships already have castType
            result = session.run("""
                MATCH ()-[r:ACTED_IN]->()
                WHERE r.castType IS NOT NULL
                RETURN count(r) as existing_count
            """)
            existing_count = result.single()['existing_count']
            print(f"Existing relationships with castType: {existing_count}")
            
            # Count total ACTED_IN relationships
            result = session.run("MATCH ()-[r:ACTED_IN]->() RETURN count(r) as total")
            total_relationships = result.single()['total']
            print(f"Total ACTED_IN relationships: {total_relationships}")
            
            if existing_count > 0:
                overwrite = input(f"\nFound {existing_count} relationships with castType already set. Overwrite? (y/n): ")
                if overwrite.lower() != 'y':
                    print("Aborted.")
                    return False
            
            print("\nUpdating relationships with castType information...")
            
            # Batch update in chunks
            chunk_size = 1000
            updated_count = 0
            
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i + chunk_size]
                
                # Prepare batch parameters
                batch_params = []
                for _, row in chunk.iterrows():
                    batch_params.append({
                        'tconst': row['tconst'],
                        'nconst': row['nconst'],
                        'castType': row['castType']
                    })
                
                # Execute batch update
                result = session.run("""
                    UNWIND $batch as row
                    MATCH (a:Actor {nconst: row.nconst})-[r:ACTED_IN]->(e:Episode {tconst: row.tconst})
                    SET r.castType = row.castType
                    RETURN count(r) as updated
                """, batch=batch_params)
                
                batch_updated = result.single()['updated']
                updated_count += batch_updated
                
                print(f"Processed batch {i//chunk_size + 1}/{(len(df) + chunk_size - 1)//chunk_size}, updated {batch_updated} relationships")
            
            print(f"\nTotal relationships updated: {updated_count}")
            
            # Verify the update
            result = session.run("""
                MATCH ()-[r:ACTED_IN]->()
                WHERE r.castType IS NOT NULL
                RETURN r.castType as castType, count(r) as count
                ORDER BY castType
            """)
            
            print("\nFinal cast type distribution in Neo4j:")
            for record in result:
                print(f"  {record['castType']}: {record['count']}")
                
        driver.close()
        print("\n✅ Successfully updated Neo4j with castType information!")
        return True
        
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        print("\nPlease make sure:")
        print("1. Neo4j is running")
        print("2. Connection settings are correct")
        print("3. Database credentials are valid")
        return False

def check_regular_cast_availability():
    """Check which series have regular cast members"""
    
    print("\nChecking regular cast availability by series...")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                MATCH (s:Series)<-[:PART_OF]-(e:Episode)<-[r:ACTED_IN]-(a:Actor)
                WHERE r.castType = 'regular'
                WITH s, count(DISTINCT a) as regular_cast_count
                ORDER BY s.primaryTitle
                RETURN s.primaryTitle as series, regular_cast_count
            """)
            
            print("\nSeries with regular cast members:")
            for record in result:
                print(f"  {record['series']}: {record['regular_cast_count']} regular cast members")
                
        driver.close()
        
    except Exception as e:
        print(f"Error checking regular cast: {e}")

if __name__ == "__main__":
    print("=== Neo4j CastType Updater ===")
    print("This script will add castType information to ACTED_IN relationships in Neo4j")
    print("using data from GraphDB-files/cleaned_episode_cast.csv")
    print()
    
    success = update_cast_types()
    
    if success:
        check_regular_cast_availability()
        print("\n🎭 You can now use the regular_cast_network.py Streamlit app!")
    else:
        print("\n❌ Failed to update Neo4j. Please check the error messages above.")