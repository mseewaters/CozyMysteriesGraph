:param {
  // Define the file path root and the individual file names required for loading.
  // https://neo4j.com/docs/operations-manual/current/configuration/file-locations/
  file_path_root: 'file:///', // Change this to the folder your script can access the files at.
  file_0: 'out_cozy_episodes.csv',
  file_1: 'out_cozy_series.csv',
  file_2: 'out_cozy_actors.csv'
};

// CONSTRAINT creation
// -------------------
//
// Create node uniqueness constraints, ensuring no duplicates for the given node label and ID property exist in the database. This also ensures no duplicates are introduced in future.
//
// NOTE: The following constraint creation syntax is generated based on the current connected database version 5.27.0.
CREATE CONSTRAINT `out_cozy_episodes.csv` IF NOT EXISTS
FOR (n: `Episode`)
REQUIRE (n.`tconst`) IS UNIQUE;
CREATE CONSTRAINT `out_cozy_series.csv` IF NOT EXISTS
FOR (n: `Series`)
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
  MERGE (n: `Episode` { `tconst`: row.`tconst` })
  SET n.`tconst` = row.`tconst`
  SET n.`primaryTitle` = row.`primaryTitle`
  SET n.`seasonNumber` = toInteger(trim(row.`seasonNumber`))
  SET n.`episodeNumber` = toInteger(trim(row.`episodeNumber`))
  SET n.`startYear` = toInteger(trim(row.`startYear`))
  SET n.`averageRating` = toFloat(trim(row.`averageRating`))
  SET n.`numVotes` = toInteger(trim(row.`numVotes`))
} IN TRANSACTIONS OF 10000 ROWS;

LOAD CSV WITH HEADERS FROM ($file_path_root + $file_1) AS row
WITH row
WHERE NOT row.`tconst` IN $idsToSkip AND NOT row.`tconst` IS NULL
CALL {
  WITH row
  MERGE (n: `Series` { `tconst`: row.`tconst` })
  SET n.`tconst` = row.`tconst`
  SET n.`primaryTitle` = row.`primaryTitle`
  SET n.`startYear` = toInteger(trim(row.`startYear`))
  SET n.`endYear` = toInteger(trim(row.`endYear`))
  SET n.`genres` = row.`genres`
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
LOAD CSV WITH HEADERS FROM ($file_path_root + $file_0) AS row
WITH row 
CALL {
  WITH row
  MATCH (source: `Episode` { `tconst`: row.`tconst` })
  MATCH (target: `Series` { `tconst`: row.`parentTconst` })
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
