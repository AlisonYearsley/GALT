import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from Pipeline.Generate.run import Generate
from Pipeline.Ingest.upload import Uploader
from dotenv import load_dotenv
import os
import certifi

load_dotenv(override=True)
print("AFTER DOTENV:", os.getenv("OPENAI_API_KEY"))
os.environ['SSL_CERT_FILE'] = certifi.where()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))



models = {
    "claude": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"],
    "gemini": ["models/gemini-2.5-flash-lite", "models/gemini-2.5-flash", "models/gemini-2.5-pro"],
    "openai": ["gpt-5.4-nano-2026-03-17", "gpt-5.4-mini-2026-03-17", "gpt-5.4-2026-03-05"],
}

api_keys = {
    "claude": os.getenv("ANTHROPIC_API_KEY"),
    "gemini": os.getenv("GEMINI_API_KEY"),
    "openai": os.getenv("OPENAI_API_KEY"),
}
uploader = Uploader(URI=URI, AUTH=AUTH)

RUNS = 3
EXPERIMENT_NAME = "BasicPrompt_GameList_Temp0"

failed = []
failed_lock = threading.Lock()


def run_provider(provider, provider_models):
    for model in provider_models:
        for run_idx in range(1, RUNS + 1):
            print(f"[{provider}] Run {run_idx}/{RUNS}: {model}")
            t_start = time.time()
            try:
                path = Generate(
                    provider_name=provider,
                    model_name=model,
                    api_key=api_keys[provider],
                    prompt1="exp1Gen.txt",
                    prompt2="csvformatSubcat.txt",
                    exp_name=EXPERIMENT_NAME,
                    run_idx=run_idx,
                )
                duration_s = round(time.time() - t_start, 2)
                print(f"[{provider}] Done run {run_idx} {model} in {duration_s}s")
                run_name = uploader.uploadFromJson(path, duration_s=duration_s)
                uploader.checkRun(run_name)
            except Exception as e:
                duration_s = round(time.time() - t_start, 2)
                print(f"[{provider}] FAILED run {run_idx} {model} after {duration_s}s: {type(e).__name__}: {e}")
                with failed_lock:
                    failed.append((provider, model, run_idx, type(e).__name__, str(e)))


with ThreadPoolExecutor(max_workers=len(models)) as executor:
    futures = {
        executor.submit(run_provider, provider, provider_models): provider
        for provider, provider_models in models.items()
    }
    for future in as_completed(futures):
        provider = futures[future]
        if future.exception():
            print(f"[{provider}] Provider thread crashed: {future.exception()}")

print("\nFinished Experiment")
if failed:
    print(f"\n{len(failed)} run(s) failed:")
    for provider, model, run_idx, err_type, msg in failed:
        print(f"  {provider} / {model} run {run_idx} — {err_type}: {msg}")
else:
    print("All runs completed successfully")