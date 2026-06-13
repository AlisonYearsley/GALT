import neo4j
from neo4j import GraphDatabase
from functools import lru_cache
from scipy.optimize import linear_sum_assignment
import numpy as np

class StructuralSimilarity():
    def __init__(self, URI, AUTH):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)


    def runDescriptionStatistics(self, run_name):
        run_id = f"run_{run_name.lower()}"
        """
        Schema setup:
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c)-[:IN_CATEGORY]-(g:Game)
            RETURN c.name AS category, collect(g.title) AS games
            ORDER BY category
        """
    
    def numCategories(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c:Category)
            RETURN collect(toLower(c.name)) AS categories
            """,
            run_id=run_id
        )
        return len(records[0]["categories"]) if records else []
    
    def get_pairAssignments(self,run_id):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(g:Game)
            RETURN g.id AS game_id, toLower(c.name) AS category
            """,
            run_id=run_id
        )
        return {(r["game_id"], r["category"]) for r in records}
    
    def exactEditDistance(self, run1, run2):
        a = self.get_pairAssignments(f"run_{run1.lower()}")
        b = self.get_pairAssignments(f"run_{run2.lower()}")
        return len(a.symmetric_difference(b))
    
    def get_assignments(self, run_id):
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c)-[:IN_CATEGORY]-(g:Game)
            RETURN c.name AS category, collect(g.title) AS games
            ORDER BY category
            """,
            run_id=run_id
        )
        assignments = {}
        for r in records:
            assignments.setdefault(r['category'],set())
            for game in r['games']:
                assignments[r['category']].add(game)
        return assignments

    def agnosticEditDistance(self, run1, run2):
        a = self.get_assignments(f"run_{run1.lower()}")
        b = self.get_assignments(f"run_{run2.lower()}")
        return agnostic_distance(a, b)

def check_disjoint(assignments,name="Assignments"):
    seen = set()
    for cluster_id, nodes in assignments.items():
        overlap = seen & nodes
        if overlap:
            raise ValueError(f"{name} has nodes {overlap} in multiple clusters")
        seen |= nodes

def old_agnostic_distance(a_assignments, b_assignments):
    print("New compare")
    a = list(a_assignments.values())
    b = list(b_assignments.values())
    #check_disjoint(a_assignments,"a")
    #check_disjoint(b_assignments,"b")
    all_nodes = set().union(*a, *b) if (a and b) else set()
    n = len(all_nodes)
    size = max(len(a), len(b), 1)
    matrix = np.zeros((size, size), dtype=int)
    for i in range(len(a)):
        for j in range(len(b)):
            matrix[i][j] = len(a[i] & b[j])
    row_ind, col_ind = linear_sum_assignment(-matrix)
    best_match = matrix[row_ind, col_ind].sum()
    return n - best_match


def agnostic_distance(a_assignments, b_assignments):
    a = list(a_assignments.values())
    b = list(b_assignments.values())

    all_nodes = set().union(*a, *b) if (a and b) else set()
    n = len(all_nodes)

    size = max(len(a), len(b), 1)
    matrix = np.zeros((size, size), dtype=int)
    for i in range(len(a)):
        for j in range(len(b)):
            matrix[i][j] = len(a[i] & b[j])

    row_ind, col_ind = linear_sum_assignment(-matrix)

    # Count unique games correctly placed, not intersection sizes
    matched_nodes = set()
    for i, j in zip(row_ind, col_ind):
        if i < len(a) and j < len(b):
            matched_nodes |= a[i] & b[j]
    best_match = len(matched_nodes)

    return n - best_match
