from Pipeline.Generate.run import Generate
from Pipeline.Ingest.upload import Uploader
from Pipeline.Compare.SyntaxicalComparer import SyntaxicalComparer
from Pipeline.Compare.StructuralSimilarity import StructuralSimilarity
from dotenv import load_dotenv
import os
import certifi

load_dotenv(override=True)
print("AFTER DOTENV:", os.getenv("OPENAI_API_KEY"))
os.environ['SSL_CERT_FILE'] = certifi.where()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
"""
models = ["claude","gemini","openai"]
api_keys = {"gemini":os.getenv("GEMINI_API_KEY"),"claude":os.getenv("ANTHROPIC_API_KEY"),"openai":os.getenv("OPENAI_API_KEY")}
uploader = Uploader(URI = URI, AUTH = AUTH)

for model in models:
    print(api_keys[model])
    print(print(os.getenv("OPENAI_API_KEY")))
    path = Generate(model_name=model,api_key=api_keys[model],prompt1="exp1Gen.txt",prompt2="csvformatSubcat.txt",exp_name="Experiment1",runs=3)
    run_name = uploader.uploadFromJson(path)
    uploader.checkRun(run_name)
print("Finished Experiment")
#uploader.uploadFromCSV(experiment_id="Test",model_id="claude",csv_path="data\\Manual\\subCatTest.csv",run_name="oldEx1ClaudeUI")

"""

import glob

uploader = Uploader(URI=URI, AUTH=AUTH)
SOURCE_EXPERIMENT = "Experiment1"   # folder to read JSONs from
TARGET_EXPERIMENT = "NewAcrossModel"            # set to a string to upload under a different experiment name


#uploader.delete(TARGET_EXPERIMENT)
for path in glob.glob(f"data/Auto/{SOURCE_EXPERIMENT}/*.json"):
    print(f"Attempting to upload {path}")
    run_name = uploader.uploadFromJson(path, override_experiment=TARGET_EXPERIMENT)
    uploader.checkRun(run_name)
print(f"Finished uploading {SOURCE_EXPERIMENT} JSONs as '{TARGET_EXPERIMENT}'")




