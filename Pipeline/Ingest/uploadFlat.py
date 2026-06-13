import csv, json, io
from neo4j import GraphDatabase


class Uploader():
    def __init__(self, URI, AUTH):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)

    def uploadGames(self):
        with open("data/Reference/Games.csv", newline="") as f:
            games = list(csv.DictReader(f))
        self.driver.execute_query(
            """
            UNWIND $games AS row
            MERGE (:Game {id: row.gameId, title: row.title})
            """,
            games=games
        )
        print(f"Uploaded {len(games)} games")

    def checkGames(self):
        records, _, _ = self.driver.execute_query("MATCH (g:Game) RETURN g.title ORDER BY g.id")
        for r in records:
            print(r["g.title"])

    def newExperiment(self, experiment_id, name):
        self.driver.execute_query(
            """
            MERGE (e:Experiment {id: $id})
            SET e.name = $name
            """,
            id=experiment_id, name=name
        )
        print(f"Created experiment: {name}")

    def newModel(self, model_id, name):
        self.driver.execute_query(
            """
            MERGE (m:Model {id: $id})
            SET m.name = $name
            """,
            id=model_id, name=name
        )
        print(f"Created model: {name}")

    def newRun(self, run_name, model_id, experiment_id):
        run_id = f"run_{run_name.lower()}"
        self.driver.execute_query(
            """
            MATCH (e:Experiment {id: $experiment_id})
            MATCH (m:Model {id: $model_id})
            MERGE (r:Run {id: $run_id})
            SET r.name = $run_name
            MERGE (e)-[:HAS_RUN]->(r)
            MERGE (r)-[:USES_MODEL]->(m)
            """,
            run_id=run_id, run_name=run_name, model_id=model_id, experiment_id=experiment_id
        )
        print(f"Created run: {run_name}")

    def delete(self, node_id):
        self.driver.execute_query(
            """
            MATCH (parent {id: $node_id})
            OPTIONAL MATCH (parent)-[:HAS_CHILD*0..]->(descendant)
            DETACH DELETE parent, descendant
            """,
            node_id=node_id
        )
        print(f"Deleted {node_id} and its children")
        
    def uploadFromCSV(self, experiment_id, model_id, csv_path, run_name):
        self.newExperiment(experiment_id=experiment_id,name=experiment_id)
        self.newModel(model_id=model_id, name=model_id)
        self.newRun(run_name=run_name, model_id=model_id, experiment_id=experiment_id)
        self._updateManifest(experiment_id, model_id, run_name, method = "CSV", manifest_path="data\\AUTO\\manifest.csv")
        with open(csv_path, newline="") as f:
            rows = list(csv.DictReader(f))
        self._uploadTaxonomyRows(rows, run_name)

    def _updateManifest(self, experiment_id, model_id, run_name, method = "Unknown", manifest_path="data\\AUTO\\manifest.csv"):
        fieldnames = ["experiment_id", "model_id", "run_name","method"]
        row={"experiment_id": experiment_id, "model_id": model_id, "run_name": run_name, "method":method}

        with open(manifest_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)
        print(f"Manifest updated: {run_name}")

    def uploadFromJson(self, json_path):
        with open(json_path) as f:
            data = json.load(f)

        self.newExperiment(experiment_id=data["experiment"],name=data["experiment"])
        self.newModel(model_id=data["model"], name=data["model"])
        self.newRun(run_name=str(data["run_index"])+data["run_id"], model_id=data["model"], experiment_id=data["experiment"])
        self._updateManifest(experiment_id=data["experiment"], model_id=data["model"], run_name=str(data["run_index"])+data["run_id"])

        csv_str = data["format"].strip()
        if csv_str.startswith("```"):
            csv_str = csv_str.split("\n", 1)[1]
        if csv_str.endswith("```"):
            csv_str = csv_str.rsplit("\n", 1)[0]
        
        reader = csv.DictReader(io.StringIO(csv_str.strip()))
        rows = [{"Category": r["Parent"], "Game": r["Child"]} for r in reader]
        self._uploadTaxonomyRows(rows, str(data["run_index"])+data["run_id"])

    def _uploadTaxonomyRows(self, rows, run_name):
        run_id = f"run_{run_name.lower()}"

        with open("data/Reference/Games.csv", newline="") as f:
            game_lookup = {row["title"]: row["gameId"] for row in csv.DictReader(f)}

        resolved = []
        for row in rows:
            game_id = game_lookup.get(row["Game"])
            if not game_id:
                print(f"Warning: '{row['Game']}' not found in games.csv")
                continue
            resolved.append({"category": row["Category"], "gameId": game_id})
        print(resolved)
        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MATCH (r:Run {id: $run_id})
            MERGE (c:Category {name: row.category, run_id: $run_id})
            MERGE (r)-[:HAS_CATEGORY]->(c)
            WITH c, row
            MATCH (g:Game {id: row.gameId})
            MERGE (g)-[:IN_CATEGORY]->(c)
            """,
            rows=resolved, run_id=run_id
        )
        print(f"Uploaded {len(resolved)} game-category relationships for {run_name,run_id}")

    def checkRun(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c)-[:IN_CATEGORY]-(g:Game)
            RETURN c.name AS category, collect(g.title) AS games
            ORDER BY category
            """,
            run_id=run_id
        )
        for r in records:
            print(f"\n{r['category']}")
            for game in r['games']:
                print(f"  - {game}")

    def checkChain(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (e:Experiment)-[:HAS_RUN]->(r:Run {id: $run_id})-[:USES_MODEL]->(m:Model)
            RETURN e.name AS experiment, m.name AS model, r.name AS run
            """,
            run_id=run_id
        )
        for r in records:
            print(f"Experiment : {r['experiment']}")
            print(f"Model      : {r['model']}")
            print(f"Run        : {r['run']}")


    
#(Experiment)-[:HAS_RUN]->(Run)-[:USES_MODEL]->(Model)
#(Run)-[:HAS_CATEGORY]->(Category)<-[:IN_CATEGORY]-(Game)
