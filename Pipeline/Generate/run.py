import os, json, uuid, csv
from datetime import datetime
#from Pipeline.Generate.Runners.ChatGPT import checkModels as openai_models
from Pipeline.Generate.Runners.Claude import checkModels as claude_models
#from Pipeline.Generate.Runners.Gemini import checkModels as gemini_models
from Pipeline.Generate.Runners.ChatGPT import run_chat as run_openai
from Pipeline.Generate.Runners.Claude import run_chat as run_claude
from Pipeline.Generate.Runners.Gemini import run_chat as run_gemini

def _load_games(games_path):
    with open(games_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return "\n".join(r["title"] for r in rows)


def Generate(provider_name="openai", model_name=None, exp_name="GeneratedTaxonomies", prompt1="taxonomy7.txt", prompt2="csvformat.txt", run_idx=1, api_key=None, temperature=1.0, games_path="data/Reference/Games.csv", pdf_path=None):
    if api_key is None:
        print("ERROR: input API key")
    PROVIDERS = {
        "openai": run_openai,
        "claude": run_claude,
        "gemini": run_gemini,
    }
    BASE_DIR = os.path.dirname(__file__)
    DATA_DIR = os.path.join("data", "Auto", exp_name)
    os.makedirs(DATA_DIR, exist_ok=True)

    games_list = _load_games(games_path)

    with open(os.path.join(BASE_DIR, "Prompts", prompt1)) as f:
        PROMPT_1 = f.read().format(games=games_list)

    with open(os.path.join(BASE_DIR, "Prompts", prompt2)) as f:
        PROMPT_2 = f.read()

    runner = PROVIDERS[provider_name]

    run_id = f"{provider_name}_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.utcnow().isoformat()
    print(f"preparing API call {run_id}")
    taxonomy = runner(messages=[PROMPT_1], api_key=api_key, model=model_name, temperature=temperature, pdf_path=pdf_path)
    format = runner(messages=[PROMPT_1, taxonomy, PROMPT_2], api_key=api_key, model=model_name, temperature=temperature, pdf_path=pdf_path)

    record = {
        "experiment": exp_name,
        "run_id": run_id,
        "timestamp": timestamp,
        "model": model_name,
        "run_index": run_idx,
        "prompt1": prompt1,
        "prompt2": prompt2,
        "temperature": temperature,
        "games_path": games_path,
        "pdf_path": pdf_path,
        "taxonomy": taxonomy,
        "format": format,
    }
    print("Api call complete. Preparing save")
    out_path = os.path.join(DATA_DIR, f"{run_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Saved {out_path}")
    return out_path



