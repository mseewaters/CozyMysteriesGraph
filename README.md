Data files:
https://developer.imdb.com/non-commercial-datasets/

Import files to Neo4j

:param {
  // Define the file path root and the individual file names required for loading.
  // https://neo4j.com/docs/operations-manual/current/configuration/file-locations/
  file_path_root: 'file:///', // Change this to the folder your script can access the files at.
  file_0: 'out_cozy_series.csv',
  file_1: 'out_cozy_episodes.csv',
  file_2: 'out_cozy_actors.csv'
};

// CONSTRAINT creation
// -------------------
//
// Create node uniqueness constraints, ensuring no duplicates for the given node label and ID property exist in the database. This also ensures no duplicates are introduced in future.
//
// NOTE: The following constraint creation syntax is generated based on the current connected database version 2025.6.1.
CREATE CONSTRAINT `tconst_Series_uniq` IF NOT EXISTS
FOR (n: `Series`)
REQUIRE (n.`tconst`) IS UNIQUE;
CREATE CONSTRAINT `tconst_Episode_uniq` IF NOT EXISTS
FOR (n: `Episode`)
REQUIRE (n.`tconst`) IS UNIQUE;
CREATE CONSTRAINT `nconst_Actor_uniq` IF NOT EXISTS
FOR (n: `Actor`)
REQUIRE (n.`nconst`) IS UNIQUE;

:param {
  idsToSkip: []
};

// NODE load
// ---------
//
// Load nodes in batches, one node label at a time. Nodes will be created using a MERGE statement to ensure a node with the same label and ID property remains unique. Pre-existing nodes found by a MERGE statement will have their other properties set to the latest values encountered in a load file.
//
// NOTE: Any nodes with IDs in the 'idsToSkip' list parameter will not be loaded.
LOAD CSV WITH HEADERS FROM ($file_path_root + $file_0) AS row
WITH row
WHERE NOT row.`tconst` IN $idsToSkip AND NOT row.`tconst` IS NULL
CALL {
  WITH row
  MERGE (n: `Series` { `tconst`: row.`tconst` })
  SET n.`tconst` = row.`tconst`
  SET n.`primaryTitle` = row.`primaryTitle`
  SET n.`startYear` = toInteger(trim(row.`startYear`))
} IN TRANSACTIONS OF 10000 ROWS;

LOAD CSV WITH HEADERS FROM ($file_path_root + $file_1) AS row
WITH row
WHERE NOT row.`tconst` IN $idsToSkip AND NOT row.`tconst` IS NULL
CALL {
  WITH row
  MERGE (n: `Episode` { `tconst`: row.`tconst` })
  SET n.`tconst` = row.`tconst`
  SET n.`primaryTitle` = row.`primaryTitle`
  SET n.`seasonNumber` = toInteger(trim(row.`seasonNumber`))
  SET n.`episodeNumber` = toInteger(trim(row.`episodeNumber`))
  SET n.`startYear` = toInteger(trim(row.`startYear`))
  SET n.`averageRating` = toFloat(trim(row.`averageRating`))
  SET n.`numVotes` = toInteger(trim(row.`numVotes`))
} IN TRANSACTIONS OF 10000 ROWS;

LOAD CSV WITH HEADERS FROM ($file_path_root + $file_2) AS row
WITH row
WHERE NOT row.`nconst` IN $idsToSkip AND NOT row.`nconst` IS NULL
CALL {
  WITH row
  MERGE (n: `Actor` { `nconst`: row.`nconst` })
  SET n.`nconst` = row.`nconst`
  SET n.`primaryName` = row.`primaryName`
  SET n.`birthYear` = toInteger(trim(row.`birthYear`))
  SET n.`deathYear` = toInteger(trim(row.`deathYear`))
} IN TRANSACTIONS OF 10000 ROWS;


// RELATIONSHIP load
// -----------------
//
// Load relationships in batches, one relationship type at a time. Relationships are created using a MERGE statement, meaning only one relationship of a given type will ever be created between a pair of nodes.
LOAD CSV WITH HEADERS FROM ($file_path_root + $file_1) AS row
WITH row 
CALL {
  WITH row
  MATCH (source: `Episode` { `tconst`: row.`parentTconst` })
  MATCH (target: `Series` { `tconst`: row.`tconst` })
  MERGE (source)-[r: `PART_OF`]->(target)
} IN TRANSACTIONS OF 10000 ROWS;

LOAD CSV WITH HEADERS FROM ($file_path_root + $file_2) AS row
WITH row 
CALL {
  WITH row
  MATCH (source: `Actor` { `nconst`: row.`nconst` })
  MATCH (target: `Episode` { `tconst`: row.`tconst` })
  MERGE (source)-[r: `ACTED_IN`]->(target)
  SET r.`characters` = row.`characters`
} IN TRANSACTIONS OF 10000 ROWS;


## Additional labels
MATCH (a:Actor)-[:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s, count(e) AS ep_count
WHERE ep_count < 8
SET a:GuestActor

MATCH (a:Actor)-[:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s, count(e) AS ep_count
WHERE ep_count < 8
MERGE (a)-[:GUEST_IN]->(s)


MATCH (a:Actor)-[:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s, count(e) AS appearances
WHERE appearances >= 8
SET a:LeadActor

MATCH (a:Actor)-[:ACTED_IN]->(:Episode)-[:PART_OF]->(s:Series)
MERGE (a)-[:ACTED_IN_SERIES]->(s)

MATCH (a:Actor)-[:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WHERE NOT a:LeadActor
WITH a, count(DISTINCT s) AS series_count, count(DISTINCT e) AS episode_count
WHERE series_count > 1 AND episode_count > 1
SET a:Shapeshifter

MATCH (a:GuestActor)-[r:ACTED_IN]->(e:Episode)
WITH a, count(DISTINCT e) AS episodeCount, count(DISTINCT r.characters) AS characterCount
WHERE episodeCount > 1 AND characterCount = 1
SET a:Repeater

MATCH (a:GuestActor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s, count(DISTINCT e) AS episodeCount, count(DISTINCT r.characters) AS characterCount
WHERE episodeCount > 1 AND characterCount > 1
SET a:ManyNamesOneFace

MATCH (s:Series)<-[:PART_OF]-(e:Episode)<-[:ACTED_IN]-(a1:Actor),
      (e)<-[:ACTED_IN]-(a2:Actor)
WHERE a1.nconst < a2.nconst
MERGE (a1)-[r:CO_STARRED_WITH {series: s.primaryTitle}]->(a2)
  ON CREATE SET r.count = 1
  ON MATCH SET r.count = r.count + 1


## Remove labels
MATCH (:Actor)-[r:GUEST_IN]->(:Series)
DELETE r

MATCH (a:Actor)
REMOVE a:GuestActor, a:LeadActor, a:Shapeshifter, a:Repeater, a:ManyNamesOneFace


## Queries
#### Number of episodes and actors by series in the DB
MATCH (s:Series)<-[:PART_OF]-(e:Episode)<-[:ACTED_IN]-(a:Actor)
RETURN s.primaryTitle AS series,
       count(DISTINCT e) AS numEpisodes,
       count(DISTINCT a) AS numActors
ORDER BY series;


#### Same character, multiple episodes
MATCH (a)-[:GUEST_IN]->(s:Series {primaryTitle: "Midsomer Murders"})
MATCH (a)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s)
WHERE NOT a:LeadActor
WITH a, collect(DISTINCT r.characters) AS chars, collect(r) AS roles
WHERE size(roles) > 1 AND size(chars) = 1 AND chars[0] IS NOT NULL
UNWIND roles AS r
WITH a, r, endNode(r) AS e
RETURN a, r, e

#### Different character, multiple episodes
MATCH (a)-[:GUEST_IN]->(s:Series {primaryTitle: "Father Brown"})
MATCH (a)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s)
WHERE NOT a:LeadActor
WITH a, collect(DISTINCT r.characters) AS chars, collect(r) AS roles
WHERE size(roles) > 1 AND size(chars) > 1
UNWIND roles AS r
WITH a, r, endNode(r) AS e
RETURN a, r, e

MATCH (a)-[:GUEST_IN]->(s:Series)
MATCH (a)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s)
WHERE NOT a:LeadActor
WITH a, s, collect(DISTINCT r.characters) AS chars, collect(r) AS roles
WHERE size(roles) > 1 AND size(chars) > 1
UNWIND roles AS r
WITH a, r, endNode(r) AS e
MATCH (e)-[p:PART_OF]->(s:Series)
RETURN a, r, e, s, p

#### Actor links from selected episode
MATCH (s:Series {primaryTitle: "Midsomer Murders"})
MATCH (e:Episode {seasonNumber: 1, episodeNumber: 2})-[:PART_OF]->(s)
MATCH (a)-[:ACTED_IN]->(e)
WHERE NOT a:LeadActor

// Find other episodes the actor appeared in (excluding this one)
MATCH (a)-[:ACTED_IN]->(other:Episode)-[:PART_OF]->(otherSeries:Series)
WHERE other <> e

RETURN a.primaryName AS actor,
       otherSeries.primaryTitle AS otherSeries,
       other.seasonNumber AS season,
       other.episodeNumber AS episode,
       other.primaryTitle AS episodeTitle
ORDER BY actor, otherSeries, season, episode

#### Actors in multiple episodes, fully connected (no series// Step 1: gather all ACTED_IN roles across episodes and series
MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WHERE NOT a:LeadActor AND (a)-[:GUEST_IN]->(s)
WITH a, collect(DISTINCT r.characters) AS chars, collect(r) AS roles

// Step 2: filter for actors with multiple appearances as different characters
WHERE size(roles) > 1 AND size(chars) > 1

// Step 3: unwind those roles to get the full graph structure
UNWIND roles AS r
WITH a, r, endNode(r) AS e
MATCH (e)-[:PART_OF]->(s:Series)
SET e.seriesTitle = s.primaryTitle
RETURN a, r, e)

#### Top-rated episodes (with series name, excluding null ratings)
MATCH (e:Episode)-[:PART_OF]->(s:Series)
WHERE e.averageRating IS NOT NULL
RETURN s.primaryTitle AS series,
       e.primaryTitle AS episodeTitle,
       e.seasonNumber AS season,
       e.episodeNumber AS episode,
       e.averageRating AS rating,
       e.numVotes AS votes
ORDER BY rating DESC, votes DESC
LIMIT 25