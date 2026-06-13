from neo4j import GraphDatabase

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "neo4j://localhost"
AUTH = ("neo4j", "uploadTest123")

driver = GraphDatabase.driver(URI, auth=AUTH)


def runQuery(query):
    with driver.session() as session:
        result = session.run(query)
        return [record.data() for record in result]
    
res = runQuery("MATCH (t:TaxonomyRun)-[:HAS_CATEGORY]->(c:Category) WITH toLower(trim(c.name)) AS category, collect(t.run_id) AS runs RETURN category, runs,size(runs) AS appears_in_n_runs ORDER BY appears_in_n_runs DESC, category")
print(res)