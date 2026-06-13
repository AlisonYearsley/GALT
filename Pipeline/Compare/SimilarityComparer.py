def mapCategoriesByGames(self, run_name_a, run_name_b):
    run_id_a = f"run_{run_name_a.lower()}"
    run_id_b = f"run_{run_name_b.lower()}"

    records, _, _ = self.driver.execute_query(
        """
        MATCH (r1:Run {id: $run_id_a})-[:HAS_CATEGORY]->(c1:Category)<-[:IN_CATEGORY]-(g:Game)
        MATCH (g)-[:IN_CATEGORY]->(c2:Category)<-[:HAS_CATEGORY]-(r2:Run {id: $run_id_b})
        RETURN c1.name AS cat_a, c2.name AS cat_b, count(g) AS shared_games
        ORDER BY cat_a, shared_games DESC
        """,
        run_id_a=run_id_a, run_id_b=run_id_b
    )

    # Group into {cat_a: [{cat_b, shared_games}, ...]}
    mapping = {}
    for r in records:
        mapping.setdefault(r["cat_a"], []).append({
            "category": r["cat_b"],
            "shared_games": r["shared_games"]
        })

    return mapping