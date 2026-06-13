import csv
from neo4j import GraphDatabase


class SyntaxicalComparer():
    def __init__(self, URI, AUTH, run1, run2):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)
        self.run1 = run1
        self.run2 = run2
        self.categories1 = self.getCategoryNames(run1)
        self.categories2 = self.getCategoryNames(run2)

    def getCategoryNames(self, run_name):
        run_id = f"run_{run_name.lower()}"
        records, _, _ = self.driver.execute_query(
            """
            MATCH (r:Run {id: $run_id})-[:HAS_CATEGORY]->(c:Category)
            RETURN collect(toLower(c.name)) AS categories
            """,
            run_id=run_id
        )
        return records[0]["categories"] if records else []

    def exactMatch(self):
        def loop(cats1,cats2):
            byCategories = {}
            for cat in cats1:
                if cat in cats2:
                    byCategories[cat] = cat
        print(f"\nCategory mapping by {self.run1} to {self.run2}")
        print(loop(self.categories1,self.categories2))
        print(f"\nCategory mapping by {self.run2} to {self.run1}")
        print(loop(self.categories2,self.categories1))

    def exactMatch(self):
        def loop(cats1,cats2):
            byCategories = {}
            for cat in cats1:
                if cat in cats2:
                    byCategories[cat] = cat
            return byCategories
        print(f"\nCategory mapping by {self.run1} to {self.run2}")
        print(loop(self.categories1,self.categories2))
        print(f"\nCategory mapping by {self.run2} to {self.run1}")
        print(loop(self.categories2,self.categories1))

    def wordMatch(self):
        def loop(cats1,cats2):
            mapping = {}
            for cat1 in cats1.keys():
                comparisons = {}
                for cat2 in cats2.keys():
                    score = 0
                    for word1 in cats1[cat1]:
                        if word1 in cats2[cat2]:
                            print("True")
                            score += 1
                    comparisons[cat2] = round(score*2/(len(cats1[cat1])+len(cats2[cat2])),2)
                mapping[cat1] = comparisons
                             
            return mapping
        
        def splitIntoWords(categories):
            splitCats = {}
            for cat in categories:
                words = cat.split(" ")
                splitCats[cat] = [word for word in words if len(word)>1]
            return splitCats 
        
        words1 = splitIntoWords(self.categories1)
        words2 = splitIntoWords(self.categories2)
        print(f"\nCategory mapping by {self.run1} to {self.run2}")
        print(loop(words1, words2))
        print(f"\nCategory mapping by {self.run2} to {self.run1}")
        print(loop(words2, words1))



