from Pipeline.Evaluate.Evaluator import Evaluator
from Pipeline.Compare.Analyse import Analyser
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import certifi

load_dotenv()
os.environ['SSL_CERT_FILE'] = certifi.where()

URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

EXPERIMENT_ID = "NewAcrossModel"

driver = GraphDatabase.driver(URI, auth=AUTH)
records, _, _ = driver.execute_query(
    "MATCH (:Experiment {id: $exp_id})-[:HAS_RUN]->(r:Run) RETURN r.name AS run_name",
    exp_id=EXPERIMENT_ID
)
run_names = [r["run_name"] for r in records]
driver.close()
print(f"Runs: {run_names}")

evaluator = Evaluator(URI=URI, AUTH=AUTH)
for run_name in run_names:
    print(f"Evaluating {run_name}...")
    result = evaluator.evaluate(experiment_id=EXPERIMENT_ID, run_name=run_name)
    print(result)

analyser = Analyser(URI=URI, AUTH=AUTH)

print("Grouping common siblings for experiment...")
analyser.groupCommonSiblingsForExperiment(experiment_id=EXPERIMENT_ID, save=True)

print("Grouping common siblings per model...")
analyser.groupCommonSiblingsForModel(experiment_id=EXPERIMENT_ID, save=True)

print("Edit distance: each run to experiment stable subgraph...")
analyser.editDistanceToExperimentSubgraph(experiment_id=EXPERIMENT_ID)

print("Edit distance: each run to its model stable subgraph...")
analyser.editDistanceToModelSubgraph(experiment_id=EXPERIMENT_ID)
