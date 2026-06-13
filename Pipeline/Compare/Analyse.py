from neo4j import GraphDatabase
import csv
from collections import defaultdict
from itertools import combinations
from Pipeline.Compare.StructuralSimilarity import agnostic_distance


class Analyser():
    def __init__(self, URI, AUTH):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)

    def catSiblingCoocurance(self, run_name, category_name):
        children = self.getCategoryContents(run_name, category_name)
        n = len(children)
        siblings = []
        for i in range(n):
            for j in range(i + 1, n):
                siblings.append(tuple(sorted((children[i], children[j]))))
        return siblings

    def fullSiblingCoocurance(self, run_name):
        allPairs = []
        categories = self.getCategoryNames(run_name)
        for category_name in categories:
            siblings = self.catSiblingCoocurance(run_name, category_name)
            allPairs = allPairs + siblings
        return allPairs

    def getCategoryNames(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY|HAS_SUBCATEGORY*1..]->(c:Category {run_id: $run_id})
            RETURN collect(toLower(c.name)) AS categories
            """,
            run_id=run_id
        )
        return records[0]["categories"] if records else []

    def getCategoryContents(self, run_name, category_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (c:Category {run_id: $run_id})
            WHERE toLower(c.name) = toLower($category_name)
            MATCH (g:Game)-[:IN_CATEGORY]->(c)
            RETURN collect(g.title) AS games
            """,
            run_id=run_id,
            category_name=category_name
        )
        return records[0]["games"] if records else []

    def getIntersection(self, arr1, arr2):
        intersectionOn1 = [x for x in arr1 if x in arr2]
        exIntersectionOn2 = [y for y in arr2 if y in arr1 and y not in intersectionOn1]
        return intersectionOn1 + exIntersectionOn2

    def compareSiblingCoocurance(self, runs):
        siblings = []
        for run in runs:
            siblings.append(tuple((run, self.fullSiblingCoocurance(run_name=run))))
        n = len(siblings)
        sharedPairs = [
            ((siblings[i][0], siblings[j][0]), self.getIntersection(siblings[i][1], siblings[j][1]), tuple((len(siblings[i][1]), len(siblings[j][1]))))
            for i in range(n) for j in range(i + 1, n)]
        sharedPairs = [(compared, len(shared), shared, lengths) for (compared, shared, lengths) in sharedPairs]
        return sharedPairs

    def describeSiblingCoocurance(self, runs):
        coocurances = self.compareSiblingCoocurance(runs)
        for (run_pair, num_in_common, _, run_pair_len) in coocurances:
            print(f"\n{run_pair} sibling coocurance")
            print(f"has {num_in_common} sibling pairs in common")
            similarities = (num_in_common / run_pair_len[0], num_in_common / run_pair_len[1])
            print(f"{run_pair[0]} similarity {similarities[0]}")
            print(f"{run_pair[1]} similarity {similarities[1]}")
            print(f"Joint similarity {sum(similarities)/2}")

    def siblingCoocuranceCypher(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY|HAS_SUBCATEGORY*1..]->(c:Category {run_id: $run_id})
            MATCH (g1:Game)-[:IN_CATEGORY]->(c)
            MATCH (g2:Game)-[:IN_CATEGORY]->(c)
            WHERE g1.id < g2.id
            RETURN collect([g1.title, g2.title]) AS pairs
            """,
            run_id=run_id
        )
        return records[0]["pairs"] if records else []

    def compareSiblingCoocuranceCypher(self, runs):
        siblings = []
        for run in runs:
            siblings.append(tuple((run, self.siblingCoocuranceCypher(run_name=run))))
        n = len(siblings)

        def getIntersection(arr1, arr2):
            intersectionOn1 = [x for x in arr1 if x in arr2]
            exIntersectionOn2 = [y for y in arr2 if y in arr1 and y not in intersectionOn1]
            return intersectionOn1 + exIntersectionOn2

        sharedPairs = [
            ((siblings[i][0], siblings[j][0]), getIntersection(siblings[i][1], siblings[j][1]), (len(siblings[i][1]), len(siblings[j][1])))
            for i in range(n) for j in range(i + 1, n)]
        sharedPairs = [(compared, len(shared), shared, lengths) for (compared, shared, lengths) in sharedPairs]
        return sharedPairs

    def commonSiblingCoocurance(self, runs):
        pair_sets = [set(self.fullSiblingCoocurance(run_name=run)) for run in runs]
        common = pair_sets[0]
        for s in pair_sets[1:]:
            common = common & s
        return list(common)
    
    def getRunsByModel(self, experiment_id):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (e:Experiment {id: $experiment_id})-[:HAS_RUN]->(r:Run)-[:USES_MODEL]->(m:Model)
            RETURN m.id AS model_id, collect(r.name) AS runs
            """,
            experiment_id=experiment_id
        )
        return {r["model_id"]: r["runs"] for r in records}

    def groupCommonSiblingsForModel(self, experiment_id, save=False):
        runs_by_model = self.getRunsByModel(experiment_id)
        results = {}
        for model_id, runs in runs_by_model.items():
            print(f"Model {model_id}: runs {runs}")
            if len(runs) < 2:
                print(f"  Skipping — need at least 2 runs")
                continue
            groups = self.groupCommonSiblings(runs)
            results[model_id] = groups
            if save:
                self._saveModelStableSubgraph(model_id, experiment_id, groups)
        return results

    def _saveModelStableSubgraph(self, model_id, experiment_id, groups):
        subgraph_id = f"stable_{model_id}_{experiment_id}"

        self.driver.execute_query(
            """
            MATCH (m:Model {id: $model_id})
            MERGE (s:StableSubgraph {id: $subgraph_id})
            SET s.experiment_id = $experiment_id, s.model_id = $model_id
            MERGE (m)-[:HAS_STABLE_SUBGRAPH]->(s)
            """,
            model_id=model_id,
            subgraph_id=subgraph_id,
            experiment_id=experiment_id
        )

        category_rows = [
            {"id": f"{subgraph_id}_group_{i}", "name": f"Group {i}"}
            for i in range(len(groups))
        ]

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MERGE (c:StableGroup {id: row.id})
            SET c.name = row.name
            WITH c, row
            MATCH (s:StableSubgraph {id: $subgraph_id})
            MERGE (s)-[:HAS_CATEGORY]->(c)
            """,
            rows=category_rows,
            subgraph_id=subgraph_id
        )

        game_rows = [
            {"group_id": f"{subgraph_id}_group_{i}", "title": title}
            for i, group in enumerate(groups)
            for title in group
        ]

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MATCH (c:StableGroup {id: row.group_id})
            MATCH (g:Game {title: row.title})
            MERGE (g)-[:IN_CATEGORY]->(c)
            """,
            rows=game_rows
        )

        print(f"  Saved {len(groups)} stable groups for model {model_id} / experiment {experiment_id}")

    def computeStability(self, experiment_id):
        runs_by_model = self.getRunsByModel(experiment_id)
        all_runs = self.getRunNames(experiment_id)
        results = {}

        def _score(runs):
            pair_sets = [
                set(self.fullSiblingCoocurance(r)) for r in runs
            ]
            total = set().union(*pair_sets) if pair_sets else set()
            always = pair_sets[0].copy() if pair_sets else set()
            for s in pair_sets[1:]:
                always &= s
            n_total = len(total)
            n_always = len(always)
            score = round(n_always / n_total, 4) if n_total else 0.0
            return {
                "total_pairs": n_total,
                "always_together": n_always,
                "stability_score": score,
            }

        for model_id, runs in runs_by_model.items():
            if len(runs) < 2:
                continue
            results[model_id] = _score(runs)

        results["experiment"] = _score(all_runs)
        return results

    def getRunNames(self, experiment_id):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (e:Experiment {id: $experiment_id})-[:HAS_RUN]->(r:Run)
            RETURN collect(r.name) AS runs
            """,
            experiment_id=experiment_id
        )
        return records[0]["runs"] if records else []

    def groupCommonSiblings(self, runs):
        pair_set = set(self.commonSiblingCoocurance(runs))
        games = {g for pair in pair_set for g in pair}
        groups = []
        for game in games:
            candidates = {g for pair in pair_set for g in pair if game in pair} | {game}
            clique = {game}
            for candidate in candidates - {game}:
                if all(tuple(sorted((candidate, m))) in pair_set for m in clique):
                    clique.add(candidate)
            if not any(clique <= existing for existing in groups):
                groups.append(clique)
        return [sorted(g) for g in groups if len(g) > 1]
    
    def groupCommonSiblingsForExperiment(self, experiment_id, save=False):
        runs = self.getRunNames(experiment_id)
        print(f"Found runs: {runs}")
        groups = self.groupCommonSiblings(runs)
        if save:
            self.saveGroupedCommonSiblings(experiment_id, groups)
        return groups

    def saveGroupedCommonSiblings(self, experiment_id, groups):
        subgraph_id = f"stable_{experiment_id}"

        self.driver.execute_query(
            """
            MATCH (e:Experiment {id: $experiment_id})
            MERGE (s:StableSubgraph {id: $subgraph_id})
            SET s.experiment_id = $experiment_id
            MERGE (e)-[:HAS_STABLE_SUBGRAPH]->(s)
            """,
            experiment_id=experiment_id,
            subgraph_id=subgraph_id
        )

        category_rows = [
            {"id": f"{subgraph_id}_group_{i}", "name": f"Group {i}"}
            for i in range(len(groups))
        ]

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MERGE (c:StableGroup {id: row.id})
            SET c.name = row.name
            WITH c, row
            MATCH (s:StableSubgraph {id: $subgraph_id})
            MERGE (s)-[:HAS_CATEGORY]->(c)
            """,
            rows=category_rows,
            subgraph_id=subgraph_id
        )

        game_rows = [
            {"group_id": f"{subgraph_id}_group_{i}", "title": title}
            for i, group in enumerate(groups)
            for title in group
        ]

        self.driver.execute_query(
            """
            UNWIND $rows AS row
            MATCH (c:StableGroup {id: row.group_id})
            MATCH (g:Game {title: row.title})
            MERGE (g)-[:IN_CATEGORY]->(c)
            """,
            rows=game_rows
        )

        print(f"Saved {len(groups)} stable groups for experiment: {experiment_id}")

    def _get_run_assignments(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY|HAS_SUBCATEGORY*1..]->(c:Category {run_id: $run_id})
            MATCH (g:Game)-[:IN_CATEGORY]->(c)
            RETURN c.name AS category, collect(g.title) AS games
            """,
            run_id=run_id
        )
        return {r["category"]: set(r["games"]) for r in records}

    def _get_stable_assignments(self, subgraph_id):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (s:StableSubgraph {id: $subgraph_id})-[:HAS_CATEGORY]->(g:StableGroup)
            MATCH (game:Game)-[:IN_CATEGORY]->(g)
            RETURN g.name AS category, collect(game.title) AS games
            """,
            subgraph_id=subgraph_id
        )
        return {r["category"]: set(r["games"]) for r in records}


    def editDistanceToExperimentSubgraph(self, experiment_id):
        subgraph_id = f"stable_{experiment_id}"
        stable = self._get_stable_assignments(subgraph_id)
        if not stable:
            print(f"No stable subgraph found for {experiment_id}")
            return {}
        run_names = self.getRunNames(experiment_id)
        results = {}
        for run_name in run_names:
            run = self._get_run_assignments(run_name)
            dist = agnostic_distance(run, stable)
            results[run_name] = dist
            print(f"  {run_name} -> {experiment_id} stable subgraph: {dist}")
        return results

    def editDistanceToModelSubgraph(self, experiment_id):
        runs_by_model = self.getRunsByModel(experiment_id)
        results = {}
        for model_id, runs in runs_by_model.items():
            subgraph_id = f"stable_{model_id}_{experiment_id}"
            stable = self._get_stable_assignments(subgraph_id)
            if not stable:
                print(f"No stable subgraph found for model {model_id}")
                continue
            results[model_id] = {}
            for run_name in runs:
                run = self._get_run_assignments(run_name)
                dist = agnostic_distance(run, stable)
                results[model_id][run_name] = dist
                print(f"  {run_name} -> {model_id} stable subgraph: {dist}")
        return results

    def load_taxonomy_from_csv(self, filepath):
        taxonomy = defaultdict(list)
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                taxonomy[row["Category"]].append(row["Game"])
        return dict(taxonomy)

    def get_sibling_pairs(self, taxonomy):
        pairs = set()
        for games in taxonomy.values():
            for a, b in combinations(sorted(games), 2):
                pairs.add((a, b))
        return pairs



