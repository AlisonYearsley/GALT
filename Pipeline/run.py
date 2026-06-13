from Pipeline.Generate.run import Generate
from Pipeline.Ingest.upload import Uploader
from Pipeline.Compare.SyntaxicalComparer import SyntaxicalComparer
from Pipeline.Compare.StructuralSimilarity import StructuralSimilarity
from Pipeline.Compare.Analyse import Analyser
from Pipeline.Evaluate.Evaluator import Evaluator
from dotenv import load_dotenv
import os
import certifi
load_dotenv()

#models = claude, openai, gemini
##Generate
"""
print("Preparing to generate")
Generate(model_name="gemini",api_key=os.getenv("GEMINI_API_KEY"),exp_name="Test")
"""


os.environ['SSL_CERT_FILE'] = certifi.where()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
"""
uploader = Uploader(URI = os.getenv("NEO4J_URI"), AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))) # Switch to env
uploader.uploadGames()
uploader.uploadFromJson("data\\AUTO\\GeneratedTaxonomies\\gemini_4bb5161f.json")
print("Upload complete")
"""

##compare
"""
comparer = SyntaxicalComparer(URI = URI, AUTH = AUTH, run1="0claude_826eaa90", run2="1gemini_4bb5161f")
comparer.exactMatch()
comparer.wordMatch()
"""
"""
structureMetrics = StructuralSimilarity(URI = URI, AUTH = AUTH)
numCats = structureMetrics.numCategories(run_name="0claude_826eaa90")
editDistance = structureMetrics.exactEditDistance(run1="0claude_826eaa90",run2="1gemini_4bb5161f")
editDistance = structureMetrics.agnosticEditDistance(run1="0claude_826eaa90",run2="1gemini_4bb5161f")
print(editDistance)
"""
"""
###Test uploader using edit distance
structureMetrics = StructuralSimilarity(URI = URI, AUTH = AUTH)
uploader = Uploader(URI = os.getenv("NEO4J_URI"), AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))
#uploader.uploadFromJson("data\\Auto\\GeneratedTaxonomies\\gemini_4bb5161f.json")
uploader.uploadFromCSV(experiment_id="GeneratedTaxonomies",model_id="gemini",csv_path="data\\Manual\\manual_taxonomy_gemini_4bb5161f.csv",run_name="manual_taxonomy_gemini_4bb5161f")

editDistance = structureMetrics.agnosticEditDistance(run1="manual_taxonomy_gemini_4bb5161f",run2="manual_format_gemini_4bb5161f")
print(editDistance)
"""
"""
## Test evaluator
evaluator = Evaluator(URI=URI, AUTH=AUTH)
cats = evaluator.evaluate(experiment_id="Experiment1", run_name="2gemini_9d3ae74f")
cats = evaluator.evaluate(experiment_id="Experiment1", run_name="1openai_55b7eaf6")
print(cats)
"""
"""
#Test Dimensional uploader
uploader = Uploader(URI = URI, AUTH = AUTH)
#uploader.uploadFromDimensionalJson(json_path = "LLMs\\data\\runs\\experiment_5\\gemini_39a2eaa5.json")
#uploader.uploadFromDimensionalJson(json_path = "LLMs\\data\\runs\\experiment_5\\openai_656d1dca.json")
uploader.uploadDimensions(json_path = "LLMs\\data\\runs\\experiment_5\\openai_656d1dca.json")
"""
"""
#Test sibling coocurrance
analyser = Analyser(URI=URI, AUTH=AUTH)
run1 = "2gemini_9d3ae74f"
run2 = "1openai_55b7eaf6"

analyser.describeSiblingCoocurance([run1, run2])
#common = analyser.groupCommonSiblings([run1, run2])
#common = analyser.groupCommonSiblingsForExperiment(experiment_id="Experiment1",save=True)
common =analyser.groupCommonSiblingsForModel(experiment_id="Experiment1",save=True)
print(common)
"""

"""
uploader = Uploader(URI = os.getenv("NEO4J_URI"), AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))
uploader.delete("stable_gpt-5.4-mini_Exp1AcrossOpenAi")
uploader.delete("stable_Exp1AcrossOpenAi")
uploader.delete("stable_gpt-5.4_Exp1AcrossOpenAi")
uploader.delete("stable_gpt-5.4-nano_Exp1AcrossOpenAi")
"""