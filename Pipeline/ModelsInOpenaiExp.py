from Pipeline.Generate.run import Generate
from Pipeline.Ingest.upload import Uploader
from Pipeline.Compare.SyntaxicalComparer import SyntaxicalComparer
from Pipeline.Compare.StructuralSimilarity import StructuralSimilarity
from dotenv import load_dotenv
import os
import certifi
import glob

load_dotenv(override=True)
print("AFTER DOTENV:", os.getenv("OPENAI_API_KEY"))
os.environ['SSL_CERT_FILE'] = certifi.where()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

provider = "openai"
models = ["gpt-5.4-mini","gpt-5.4-nano"]

api_keys = {"openai":os.getenv("OPENAI_API_KEY")}
uploader = Uploader(URI = URI, AUTH = AUTH)
"""
for model in models:
    Generate(provider_name = "openai",model_name=model,api_key=api_keys[provider],prompt1="exp1Gen.txt",prompt2="csvformatSubcat.txt",exp_name="Exp1AcrossOpenAi",runs=3)
print("Finished Experiment")



"""


for path in glob.glob("data/Auto/Exp1AcrossOpenAi/*.json"):
    print(f"Attempting to upload {path}")
    run_name = uploader.uploadFromJson(path)
    uploader.checkRun(run_name)
print("Finished uploading OpenAi JSONs")


#uploader.delete("Exp1AcrossOpenAi")