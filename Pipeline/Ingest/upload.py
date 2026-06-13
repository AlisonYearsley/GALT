import csv, json, io, os
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
            OPTIONAL MATCH (parent)-[:HAS_RUN|HAS_CATEGORY|HAS_SUBCATEGORY*0..]->(descendant)
            DETACH DELETE parent, descendant
            """,
            node_id=node_id
        )
        print(f"Deleted {node_id} and its children")
        
    def uploadFromCSV(self, experiment_id, model_id, csv_path, run_name):
        self.newExperiment(experiment_id=experiment_id,name=experiment_id)
        self.newModel(model_id=model_id, name=model_id)
        self.newRun(run_name=run_name, model_id=model_id, experiment_id=experiment_id)
        self._updateManifest(experiment_id, model_id, run_name, method = "CSV", manifest_path="data\\AUTO\\upload_manifest.csv")
        with open(csv_path, newline="") as f:
            rows = list(csv.DictReader(f))
        self._uploadTaxonomyRows(rows, run_name)

    def _updateManifest(self, experiment_id, model_id, run_name, method="Unknown", duration_s=None, prompt1=None, prompt2=None, temperature=None, games_path=None, data_path=None, manifest_path="data\\AUTO\\upload_manifest.csv"):
        fieldnames = ["experiment_id", "model_id", "run_name", "method", "duration_s", "prompt1", "prompt2", "temperature", "games_path", "data_path"]
        row = {"experiment_id": experiment_id, "model_id": model_id, "run_name": run_name, "method": method, "duration_s": duration_s, "prompt1": prompt1, "prompt2": prompt2, "temperature": temperature, "games_path": games_path, "data_path": data_path}

        import os
        write_header = not os.path.exists(manifest_path) or os.path.getsize(manifest_path) == 0
        with open(manifest_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        print(f"Manifest updated: {run_name}")

    def uploadFromJson(self, json_path, duration_s=None, override_experiment=None):
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        experiment_id = override_experiment or data["experiment"]
        self.newExperiment(experiment_id=experiment_id, name=experiment_id)
        self.newModel(model_id=data["model"], name=data["model"])
        self.newRun(run_name=str(data["run_index"])+data["run_id"], model_id=data["model"], experiment_id=experiment_id)
        self._updateManifest(
            experiment_id=experiment_id,
            model_id=data["model"],
            run_name=str(data["run_index"])+data["run_id"],
            method="JSONselfCSVFormat",
            duration_s=duration_s,
            prompt1=data.get("prompt1"),
            prompt2=data.get("prompt2"),
            temperature=data.get("temperature"),
            games_path=data.get("games_path"),
            data_path=json_path,
        )

        csv_str = data["format"].strip()
        # Strip opening ```csv / ``` fence and any prose before the header
        if "```" in csv_str:
            inner = csv_str.split("```", 1)[1]  # after first ```
            inner = inner.split("```", 1)[0]    # before closing ```
            # drop optional language tag (e.g. "csv\n")
            if "\n" in inner:
                first_line, rest = inner.split("\n", 1)
                csv_str = rest if first_line.strip().lower() in ("csv", "") else inner
            else:
                csv_str = inner
        # Skip any prose lines before the header row
        lines = csv_str.strip().splitlines()
        header_idx = next(
            (i for i, l in enumerate(lines) if l.strip().lower().startswith("type")),
            0
        )
        csv_str = "\n".join(lines[header_idx:])

        rows = list(csv.DictReader(io.StringIO(csv_str.strip())))
        self._uploadTaxonomyRows(rows, str(data["run_index"])+data["run_id"])
        return str(data["run_index"])+data["run_id"]
    
    def uploadFromDimensionalJson(self, json_path):
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        run_name = str(data["run_index"]) + data["run_id"]
        taxonomy = json.loads(data["taxonomy"])

        self.newExperiment(experiment_id=data["experiment"], name=data["experiment"])
        self.newModel(model_id=data["model"], name=data["model"])
        self.newRun(run_name=run_name, model_id=data["model"], experiment_id=data["experiment"])
        self._updateManifest(
            experiment_id=data["experiment"],
            model_id=data["model"],
            run_name=run_name,
            method="JSONdimensional"
        )

        hierarchy = taxonomy["derived_hierarchy"]
        node_map = {n["node_id"]: n for n in hierarchy["nodes"]}

        rows = []

        # Category rows
        for node in hierarchy["nodes"]:
            parent_id = node.get("parent_id", "")
            if not parent_id:
                parent_label = ""
            else:
                parent_node = node_map.get(parent_id)
                parent_label = parent_node["label"] if parent_node else ""
            rows.append({
                "Type": "category",
                "Name": node["label"].strip(),
                "Parent": parent_label
            })

        # Game rows
        for m in hierarchy["membership"]:
            leaf = node_map.get(m["leaf_node_id"])
            if not leaf:
                print(f"Warning: leaf_node_id '{m['leaf_node_id']}' not found for '{m['game']}'")
                continue
            rows.append({
                "Type": "game",
                "Name": m["game"],
                "Parent": leaf["label"].strip()
            })

        self._uploadTaxonomyRows(rows, run_name)
        return run_name
    def uploadDimensions(self, json_path):
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        run_name = str(data["run_index"]) + data["run_id"]
        run_id = f"run_{run_name.lower()}"
        taxonomy = json.loads(data["taxonomy"])

        with open("data/Reference/Games.csv", newline="") as f:
            game_lookup = {row["title"]: row["gameId"] for row in csv.DictReader(f)}

        #create dimension nodes
        dimension_rows = [
            {
                "dim_id": d["dim_id"],
                "name": d["name"],
                "definition": d.get("definition", "")
            }
            for d in taxonomy["dimensions"]
        ]

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MERGE (d:Dimension {dim_id: row.dim_id, run_id: $run_id})
            SET d.name = row.name, d.definition = row.definition
            """,
            rows=dimension_rows, run_id=run_id
        )

        # create DimValue nodes and link
        value_rows = []
        for d in taxonomy["dimensions"]:
            for v in d["values"]:
                value_rows.append({
                    "dim_id": d["dim_id"],
                    "value_id": v["value_id"],
                    "label": v["label"],
                    "definition": v.get("definition", "")
                })

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MERGE (v:DimValue {value_id: row.value_id, run_id: $run_id})
            SET v.label = row.label, v.definition = row.definition
            WITH v, row
            MATCH (d:Dimension {dim_id: row.dim_id, run_id: $run_id})
            MERGE (d)-[:HAS_VALUE]->(v)
            """,
            rows=value_rows, run_id=run_id
        )

        # link run and dimensions
        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MATCH (r:Run {run_id: $run_id})
            MATCH (d:Dimension {dim_id: row.dim_id, run_id: $run_id})
            MERGE (r)-[:HAS_DIMENSION]->(d)
            """,
            rows=dimension_rows, run_id=run_id
        )

        # assign games to dimesnions
        assignment_rows = []
        for game in taxonomy["games"]:
            game_id = game_lookup.get(game["game"])
            if not game_id:
                print(f"Warning: '{game['game']}' not found in Games.csv")
                continue
            for a in game["assignments"]:
                assignment_rows.append({
                    "gameId": game_id,
                    "value_id": a["value_id"],
                    "confidence": a["confidence"],
                    "rationale": a.get("rationale", "")
                })

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MATCH (g:Game {id: row.gameId})
            MATCH (v:DimValue {value_id: row.value_id, run_id: $run_id})
            MERGE (g)-[r:ASSIGNED {run_id: $run_id}]->(v)
            SET r.confidence = row.confidence, r.rationale = row.rationale
            """,
            rows=assignment_rows, run_id=run_id
        )

        print(f"Uploaded {len(dimension_rows)} dimensions, {len(value_rows)} values, "f"{len(assignment_rows)} assignments for {run_name}")
        
    def _uploadTaxonomyRows(self, rows, run_name):
        run_id = f"run_{run_name.lower()}"

        with open("data/Reference/Games.csv", newline="") as f:
            game_lookup = {row["title"]: row["gameId"] for row in csv.DictReader(f)}

        category_rows = []
        game_rows = []
        print(f"Total rows: {len(rows)}")
        print(f"First 3 rows: {rows[:3]}")

        num_hallucinations = 0
        hallucinated_names = []
        seen_games = {}  # gameId -> first category assigned
        hybrids = {}     # gameId -> [all categories]
        for row in rows:
            if row["Type"] == "category":
                parent = row["Parent"].strip()
                category_rows.append({
                    "name": row["Name"].strip(),
                    "parent": parent if parent != "" else None
                })
            elif row["Type"] == "game":
                game_id = game_lookup.get(row["Name"])
                if not game_id:
                    print(f"Warning: '{row['Name']}' not found in games.csv")
                    num_hallucinations += 1
                    hallucinated_names.append(row["Name"])
                    continue
                category = row["Parent"]
                if game_id not in seen_games:
                    seen_games[game_id] = category
                    game_rows.append({"gameId": game_id, "category": category})
                hybrids.setdefault(game_id, []).append(category)

        # Games assigned to more than one category
        hybrid_games = {gid: cats for gid, cats in hybrids.items() if len(cats) > 1}
        if hybrid_games:
            self._saveHybrids(run_name, hybrid_games, game_lookup)

        # Create all category nodes
        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MERGE (c:Category {name: row.name, run_id: $run_id})
            WITH c, row
            WHERE row.parent IS NULL OR row.parent = ""
            MATCH (r:Run {id: $run_id})
            MERGE (r)-[:HAS_CATEGORY]->(c)
            """,
            rows=category_rows, run_id=run_id
        )

        # Create parent->child relationships
        self.driver.execute_query(
            """
            UNWIND $rows AS row
            WITH row
            WHERE row.parent IS NOT NULL
            MATCH (p:Category {name: row.parent, run_id: $run_id})
            MATCH (c:Category {name: row.name, run_id: $run_id})
            MERGE (p)-[:HAS_SUBCATEGORY]->(c)
            """,
            rows=category_rows, run_id=run_id
        )

        # Link games
        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MATCH (c:Category {name: row.category, run_id: $run_id})
            MATCH (g:Game {id: row.gameId})
            MERGE (g)-[:IN_CATEGORY]->(c)
            """,
            rows=game_rows, run_id=run_id
        )
        num_matched = len({r["gameId"] for r in game_rows})
        num_model_games = num_matched + num_hallucinations
        self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})
            SET r.num_matched_games = $num_matched,
                r.num_hallucinations = $num_hallucinations,
                r.num_model_games = $num_model_games,
                r.hallucinated_names = $hallucinated_names,
                r.num_hybrids = $num_hybrids
            """,
            run_id=run_id,
            num_matched=num_matched,
            num_hallucinations=num_hallucinations,
            num_model_games=num_model_games,
            hallucinated_names=hallucinated_names,
            num_hybrids=len(hybrid_games),
        )
        if hallucinated_names:
            print(f"  Hallucinated games ({num_hallucinations}): {hallucinated_names}")
        if hybrid_games:
            print(f"  Hybrid games ({len(hybrid_games)}): assigned to first category only")
        print(f"Uploaded {len(category_rows)} categories and {num_matched} games ({num_hallucinations} hallucinated) for {run_name}")

    def _saveHybrids(self, run_name, hybrid_games, game_lookup):
        path = "data/Auto/hybrid_games.csv"
        fields = ["run_name", "game", "categories", "num_categories"]
        title_lookup = {v: k for k, v in game_lookup.items()}
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if write_header:
                writer.writeheader()
            for game_id, cats in hybrid_games.items():
                writer.writerow({
                    "run_name": run_name,
                    "game": title_lookup.get(game_id, game_id),
                    "categories": "; ".join(cats),
                    "num_categories": len(cats),
                })
        print(f"  Saved {len(hybrid_games)} hybrid game(s) to {path}")

    def checkRun(self, run_name):
        run_id = f"run_{run_name.lower()}"
        cat_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c)
            OPTIONAL MATCH (c)<-[:IN_CATEGORY]-(g:Game)
            RETURN c.name AS category, collect(g.title) AS games
            ORDER BY category
            """,
            run_id=run_id
        )
        sub_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c)-[:HAS_SUBCATEGORY]->(sub)
            OPTIONAL MATCH (sub)<-[:IN_CATEGORY]-(g:Game)
            RETURN c.name AS category, sub.name AS subcategory, collect(g.title) AS games
            ORDER BY category, subcategory
            """,
            run_id=run_id
        )
        sub_map = {}
        for r in sub_records:
            sub_map.setdefault(r["category"], {})[r["subcategory"]] = r["games"]

        for r in cat_records:
            cat = r["category"]
            print(f"\n{cat}")
            for game in r["games"]:
                print(f"  - {game}")
            for sub, games in sub_map.get(cat, {}).items():
                print(f"  > {sub}")
                for game in games:
                    print(f"      - {game}")

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
