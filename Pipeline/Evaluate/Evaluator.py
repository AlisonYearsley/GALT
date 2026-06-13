import csv
import os
import statistics
from neo4j import GraphDatabase


class Evaluator():
    def __init__(self, URI, AUTH):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)

    def evaluate(self, experiment_id, run_name, manifest_path="data/Auto/evaluate_manifest.csv"):
        run_id = f"run_{run_name.lower()}"

        # Top-level category count
        cat_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c:Category)
            RETURN count(c) AS count
            """,
            run_id=run_id
        )
        num_categories = cat_records[0]["count"]

        # Subcategory count
        subcat_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(:Category)-[:HAS_SUBCATEGORY]->(s:Category)
            RETURN count(s) AS count
            """,
            run_id=run_id
        )
        num_subcategories = subcat_records[0]["count"]

        # Games per top-level category
        dist_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c:Category)
            OPTIONAL MATCH (c)-[:HAS_SUBCATEGORY*0..]->(node:Category)<-[:IN_CATEGORY]-(g:Game)
            RETURN c.name AS category, count(DISTINCT g) AS game_count
            ORDER BY category
            """,
            run_id=run_id
        )
        distribution = {rec["category"]: rec["game_count"] for rec in dist_records}
        counts = list(distribution.values())

        if counts:
            dist_min = min(counts)
            dist_max = max(counts)
            dist_mean = round(statistics.mean(counts), 2)
            dist_stdev = round(statistics.stdev(counts), 2) if len(counts) > 1 else 0.0
        else:
            dist_min = dist_max = dist_mean = dist_stdev = 0

        # Total number of games (leaf nodes)
        leaf_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY|HAS_SUBCATEGORY*]->(:Category)<-[:IN_CATEGORY]-(g:Game)
            RETURN count(DISTINCT g) AS count
            """,
            run_id=run_id
        )
        num_leafs = leaf_records[0]["count"]

        # Average path length from Run to game
        path_records, _, _ = self.driver.execute_query(
            """
            MATCH path = (r:Run {id: $run_id})-[:HAS_CATEGORY|HAS_SUBCATEGORY*]->(:Category)<-[:IN_CATEGORY]-(g:Game)
            RETURN round(avg(length(path)), 2) AS avg_path_length
            """,
            run_id=run_id
        )
        avg_path_length = path_records[0]["avg_path_length"] or 0.0

        # Edge-to-node ratio
        graph_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})
            OPTIONAL MATCH (r)-[:HAS_CATEGORY]->(c:Category)
            OPTIONAL MATCH (c)-[:HAS_SUBCATEGORY*1..]->(sub:Category)
            OPTIONAL MATCH (c)<-[:IN_CATEGORY]-(g1:Game)
            OPTIONAL MATCH (sub)<-[:IN_CATEGORY]-(g2:Game)
            WITH
                1 + count(DISTINCT c) + count(DISTINCT sub) + count(DISTINCT g1) + count(DISTINCT g2) AS num_nodes,
                count(DISTINCT c) + count(DISTINCT sub) + count(DISTINCT g1) + count(DISTINCT g2) AS num_edges
            RETURN
                num_nodes,
                num_edges
            """,
            run_id=run_id
        )
        num_nodes = graph_records[0]["num_nodes"] if graph_records else 0
        num_edges = graph_records[0]["num_edges"] if graph_records else 0
        edge_node_ratio = (num_edges, num_nodes)

        # Recall / precision / F1 / hallucinations
        coverage_records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})
            RETURN
                coalesce(r.num_matched_games, 0)   AS num_matched,
                coalesce(r.num_hallucinations, 0)  AS num_hallucinations,
                coalesce(r.num_model_games, 0)     AS num_model_games,
                coalesce(r.hallucinated_names, []) AS hallucinated_names
            """,
            run_id=run_id
        )
        ref_total_records, _, _ = self.driver.execute_query(
            "MATCH (g:Game) RETURN count(g) AS total"
        )
        ref_total = ref_total_records[0]["total"] or 0
        num_matched = coverage_records[0]["num_matched"]
        num_hallucinations = coverage_records[0]["num_hallucinations"]
        num_model_games = coverage_records[0]["num_model_games"]
        hallucinated_names = coverage_records[0]["hallucinated_names"]

        recall = round(num_matched / ref_total, 4) if ref_total else 0.0
        precision = round(num_matched / num_model_games, 4) if num_model_games else 0.0
        f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) else 0.0

        result = {
            "experiment_id": experiment_id,
            "run_name": run_name,
            "num_categories": num_categories,
            "num_subcategories": num_subcategories,
            "distribution": distribution,
            "min": dist_min,
            "mean": dist_mean,
            "max": dist_max,
            "stdev": dist_stdev,
            "avg_path_length": avg_path_length,
            "edge_node_ratio": edge_node_ratio,
            "num_leafs": num_leafs,
            "num_matched": num_matched,
            "num_hallucinations": num_hallucinations,
            "hallucinated_names": hallucinated_names,
            "num_model_games": num_model_games,
            "recall": recall,
            "precision": precision,
            "f1": f1,
        }

        self._saveToManifest(result, manifest_path)
        self._saveMetricsNode(result)
        return result

    def _saveToManifest(self, result, manifest_path):
        fieldnames = ["experiment_id", "run_name", "num_categories", "num_subcategories", "num_leafs", "min", "mean", "max", "stdev", "avg_path_length", "edge_node_ratio", "recall", "precision", "f1", "num_hallucinations", "hallucinated_names", "distribution"]
        row = {
            "experiment_id": result["experiment_id"],
            "run_name": result["run_name"],
            "num_categories": result["num_categories"],
            "num_subcategories": result["num_subcategories"],
            "num_leafs": result["num_leafs"],
            "min": result["min"],
            "mean": result["mean"],
            "max": result["max"],
            "stdev": result["stdev"],
            "avg_path_length": result["avg_path_length"],
            "edge_node_ratio": result["edge_node_ratio"],
            "recall": result["recall"],
            "precision": result["precision"],
            "f1": result["f1"],
            "num_hallucinations": result["num_hallucinations"],
            "hallucinated_names": "; ".join(result["hallucinated_names"]),
            "distribution": str(result["distribution"]),
        }

        write_header = not os.path.exists(manifest_path) or os.path.getsize(manifest_path) == 0
        with open(manifest_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        print(f"Saved evaluation for {result['run_name']}: {result['num_categories']} cats, {result['num_subcategories']} subcats, games/cat min={result['min']} mean={result['mean']} max={result['max']} σ={result['stdev']}")

    def _saveMetricsNode(self, result):
        run_id = f"run_{result['run_name'].lower()}"
        self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})
            MERGE (r)-[:HAS_METRICS]->(m:Metrics {run_id: $run_id})
            SET m.num_categories = $num_categories,
                m.num_subcategories = $num_subcategories,
                m.dist_min = $dist_min,
                m.dist_mean = $dist_mean,
                m.dist_max = $dist_max,
                m.dist_stdev = $dist_stdev,
                m.avg_path_length = $avg_path_length,
                m.num_edges = $num_edges,
                m.num_nodes = $num_nodes,
                m.num_leafs = $num_leafs,
                m.recall = $recall,
                m.precision = $precision,
                m.f1 = $f1,
                m.num_hallucinations = $num_hallucinations
            """,
            run_id=run_id,
            num_categories=result["num_categories"],
            num_subcategories=result["num_subcategories"],
            dist_min=result["min"],
            dist_mean=result["mean"],
            dist_max=result["max"],
            dist_stdev=result["stdev"],
            avg_path_length=result["avg_path_length"],
            num_edges=result["edge_node_ratio"][0],
            num_nodes=result["edge_node_ratio"][1],
            num_leafs=result["num_leafs"],
            recall=result["recall"],
            precision=result["precision"],
            f1=result["f1"],
            num_hallucinations=result["num_hallucinations"],
        )
        print(f"Saved metrics node for {result['run_name']}")
