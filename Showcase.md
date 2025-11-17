streamlit run userApps\presentation_app.py

start the neo4j database
streamlit run userApps/mystery_graph.py

# Import -> Files -> actor, episode, series

Nodes
    Series: tconst (key), primaryTitle, startYear
    Episode: tconst (key), primaryTitle, seasonNumber, episodeNumber, startYear, averageRating
    Actor: nconst (key), primaryName, birthYear
Relationships
    ACTED_IN:  actors, from actor nconst to episode tconst, character:characters
    PART_OF: episodes, from episode tconst to series parentTconst

# Run Import

## See all series:
MATCH (s:Series) RETURN s.primaryTitle AS series

## See number of episodes per series:
MATCH (e:Episode)-[:PART_OF]->(s:Series)
RETURN s.primaryTitle AS series, count(e) AS episodes
ORDER BY episodes DESC

## See series and episodes visually
MATCH (e:Episode)-[p:PART_OF]->(s:Series) 
RETURN s,e,p

## See actors in multiple series
MATCH (a:Actor)-[:ACTED_IN]->(:Episode)-[:PART_OF]->(s:Series)
WITH a, collect(DISTINCT s.primaryTitle) AS shows
WHERE size(shows) > 1
RETURN a.primaryName AS Actor, shows, size(shows) AS seriesCount
ORDER BY seriesCount DESC, Actor
LIMIT 10;

## Show shortest path
MATCH path = shortestPath(
  (a1:Actor {primaryName:'Ralf Little'})-[:ACTED_IN*..4]-(a2:Actor {primaryName:'Amanda Redman'})
)
RETURN path;

## Materialize role type:
// start clean each refresh
MATCH ()-[r:ROLE_IN_SERIES]->() DELETE r;

MATCH (a:Actor)-[r:ACTED_IN]->(e:Episode)-[:PART_OF]->(s:Series)
WITH a, s,
     toLower(trim(coalesce(r.characters,''))) AS character,
     collect(DISTINCT e) AS eps
WHERE character <> ''
WITH a, s, character, size(eps) AS cnt
MERGE (a)-[ris:ROLE_IN_SERIES {seriesId: s.tconst, character: character}]->(s)
SET ris.episodeCount = cnt,
    ris.status = CASE
                   WHEN cnt < 2  THEN 'guest'
                   WHEN cnt <= 10 THEN 'recurring'
                   ELSE 'main'
                 END,
    ris.updatedAt = datetime();

## Show the guests in multiple episodes
WITH 1 AS minEps, 8 AS maxEps
MATCH (a:Actor)-[ris:ROLE_IN_SERIES]->(s:Series)
WHERE ris.status = 'guest'
  AND ris.episodeCount >= minEps AND ris.episodeCount <= maxEps
MATCH (a)-[ra:ACTED_IN]->(e:Episode)-[p:PART_OF]->(s)
WHERE toLower(trim(coalesce(ra.characters,''))) = ris.character
RETURN a, ra, e, p AS ep, s
ORDER BY a.primaryName, s.primaryTitle, ep.seasonNumber, ep.episodeNumber
LIMIT 600;