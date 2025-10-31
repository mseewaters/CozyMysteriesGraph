Import -> Files -> actor, episode, series

Nodes
    Series: tconst (key), primaryTitle, startYear
    Episode: tconst (key), primaryTitle, seasonNumber, episodeNumber, startYear, averageRating
    Actor: nconst (key), primaryName, birthYear
Relationships
    ACTED_IN:  actors, from actor nconst to episode tconst, character:characters
    PART_OF: episodes, from episode tconst to series parentTconst

Run Import

See all series:
MATCH (s:Series) RETURN s.primaryTitle AS series

See number of episodes per series:
MATCH (e:Episode)-[:PART_OF]->(s:Series)
RETURN s.primaryTitle AS series, count(e) AS episodes
ORDER BY episodes DESC

See series and episodes visually
MATCH (e:Episode)-[p:PART_OF]->(s:Series) 
RETURN s,e,p

