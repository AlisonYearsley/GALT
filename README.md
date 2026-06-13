# GALT
<<<<<<< HEAD

Python-Neo4j pipeline for generation and evaluation of LLM taxonomies as knowledge graphs
Graph Analysis of LLM Taxonomies (GALT)

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Tested on 3.14 |
| Neo4j Aura instance | Free tier works; obtain URI, username, and password from the Aura console |
| Anthropic API key | For Claude models |
| OpenAI API key | For GPT models |
| Google AI API key | For Gemini models |

---

## Installation

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install networkx matplotlib scipy   # required for analysis scripts
```

---

## Configuration

Create a `.env` file in the project root (copy the template below and fill in your credentials):

```
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...
OPENAI_API_KEY=sk-...

NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
AURA_INSTANCEID=<instance-id>
AURA_INSTANCENAME=<instance-name>
```

The pipeline loads this file automatically via `python-dotenv`.

---

## Reference Data

`data/Reference/Games.csv` contains the 42 Nikoli puzzle games used in every experiment. Each row has a `title` column. This file is read at generation time to build the game list injected into prompts, and at analysis time as the ground truth for recall/precision scoring.

To run the pipeline on a different game set, replace this file — no other changes are needed.

---

## Pipeline Overview

```
Generate  →  Ingest  →  Evaluate  →  Analyse
(LLM API)   (Neo4j)   (metrics)    (analysis/)
```

Each stage can be run independently. Raw LLM outputs are stored as JSON files in `data/Auto/<experiment_name>/`, so you can re-ingest or re-analyse without repeating the LLM calls.

---

## Stage 1 — Generate

Sends two sequential prompts to each model:

1. **Taxonomy prompt** — asks the model to produce a taxonomy of the 42 games.
2. **Format prompt** — asks the model to reformat its taxonomy as a CSV with columns `Type, Name, Parent`.

Each run is saved as a JSON file in `data/Auto/<experiment_name>/`.

### Run a single generation

Edit the Generate block in `Pipeline/run.py` and run:

```bash
python -m Pipeline.run
```

Or call directly from Python:

```python
from Pipeline.Generate.run import Generate
import os
from dotenv import load_dotenv
load_dotenv()

Generate(
    provider_name="claude",           # "claude", "openai", or "gemini"
    model_name="claude-sonnet-4-6",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    prompt1="exp1Gen.txt",            # taxonomy prompt (Pipeline/Generate/Prompts/)
    prompt2="csvformatSubcat.txt",    # format prompt
    exp_name="MyExperiment",          # output folder under data/Auto/
    run_idx=1,
    temperature=0.0,
    # pdf_path="data/Reference/Game_Rules.pdf"  # optional: supply rules PDF
)
```

Output: `data/Auto/MyExperiment/<provider>_<uuid>.json`

### Run a full experiment (all models, multiple runs)

Configure `Pipeline/BulkGenerate.py` and run:

```bash
python -m Pipeline.BulkGenerate
```

Key settings at the top of the file:

```python
RUNS = 3                          # runs per model
EXPERIMENT_NAME = "MyExperiment"  # output folder name
```

Models are defined in the `models` dict. All three providers run in parallel threads; within each provider, models and runs execute sequentially. Each run is uploaded to Neo4j automatically on completion.

### Available prompts

| File | Description |
|---|---|
| `exp1Gen.txt` | Basic prompt — "generate a taxonomy of grid-based logic games" |
| `taxonomy7.txt` | Richer prompt specifying category examples |
| `csvformat.txt` | Format prompt for flat (no subcategories) output |
| `csvformatSubcat.txt` | Format prompt allowing subcategories |

---

## Stage 2 — Ingest

Parses the CSV embedded in each JSON file and writes the taxonomy to Neo4j as a graph of `Run`, `Category`, and `Game` nodes.

### Upload a single run

```python
from Pipeline.Ingest.upload import Uploader
from dotenv import load_dotenv
import os
load_dotenv()

uploader = Uploader(
    URI=os.getenv("NEO4J_URI"),
    AUTH=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
uploader.uploadFromJson("data/Auto/MyExperiment/claude_abc123.json")
```

### Re-upload existing JSON files

If you need to upload runs that were already generated (e.g. under a different experiment name), configure and run `Pipeline/BulkUpload.py`:

```bash
python -m Pipeline.BulkUpload
```

---

## Stage 3 — Evaluate

Queries Neo4j to compute structural metrics for each run, builds stable subgraphs (sets of games that are always grouped together across runs), and computes edit distances from each run to those subgraphs.

```bash
python -m Pipeline.SummariseMetrics --experiment MyExperiment
```

Outputs:

| File | Description |
|---|---|
| `data/Auto/MyExperiment/summary_table.csv` | Per-run structural metrics |
| `data/Auto/MyExperiment/edit_distances.csv` | Per-run edit distances to stable subgraphs |
| `data/Auto/MyExperiment/stability.csv` | Sibling co-occurrence stability scores |
| `data/Auto/model_averages.csv` | Per-model averages (appended across experiments) |
| `data/Auto/subgraph_stats.csv` | Stable subgraph coverage statistics (appended) |

**Note:** Edit distances require stable subgraphs to exist in Neo4j first. These are built automatically when runs are uploaded via `BulkGenerate.py`, or can be triggered manually:

```python
from Pipeline.Compare.Analyse import Analyser
analyser = Analyser(URI=URI, AUTH=AUTH)
analyser.groupCommonSiblingsForModel(experiment_id="MyExperiment", save=True)
```

### Metrics reference

| Metric | Description |
|---|---|
| `num_categories` | Top-level categories in the taxonomy |
| `num_subcategories` | Second-level categories |
| `recall` / `precision` / `f1` | Fraction of the 42 reference games correctly placed |
| `edit_dist_model` | Agnostic edit distance from each run to the model's stable subgraph |
| `edit_dist_experiment` | Agnostic edit distance from each run to the experiment-wide stable subgraph |
| `stability_score` | Pairs always co-occurring / pairs ever co-occurring across all runs |

The agnostic edit distance uses Hungarian-matched optimal alignment — category labels are ignored and only set membership is compared.

---

## Stage 4 — Analysis

Standalone scripts in `analysis/` read the JSON files and CSVs directly. No Neo4j connection is needed.

> All analysis scripts cap at **3 runs per (condition × model)** to match the Neo4j-derived metrics in `model_averages.csv`.

### Consensus threshold sweep

Evaluates how the fraction of games covered by stable sibling groups varies with the co-occurrence threshold τ (swept from 1.0 to 0.5):

```bash
python analysis/consensus_threshold/analyse_tau.py
```

Outputs plots and `consensus_threshold_results.csv` to `analysis/consensus_threshold/`.

To plot only the 10-run models with List and Rules conditions overlaid:

```bash
python analysis/consensus_threshold/plot_10run_combined.py
```

### Marginal means table

Computes per-factor marginal means across model, temperature, content type, and prompt:

```bash
# 1. Compute consensus coverage at τ=1.0 and τ=0.8 for each factor level
python analysis/summary_table/compute_consensus.py

# 2. Compute mean pairwise agnostic edit distance between runs
python analysis/summary_table/compute_pairwise_edit.py

# 3. Build and render the table (PDF, PNG, CSV, LaTeX)
python analysis/summary_table/build_marginal_table.py
```

Outputs: `analysis/summary_table/marginal_means.{pdf,png,csv,tex}`

### Calculation breakdown

Shows the full pair-frequency workings behind every consensus value — which pairs survive each threshold, which cliques form, and how coverage is computed:

```bash
python analysis/summary_table/show_calculations.py
```

Outputs `calculation_breakdown.txt` (human-readable) and `calculation_breakdown.csv`.

---

## Project Structure

```
├── Pipeline/
│   ├── Generate/
│   │   ├── run.py                  # Generate() entry point
│   │   ├── Runners/                # Claude, ChatGPT, Gemini API wrappers
│   │   └── Prompts/                # Taxonomy and format prompt text files
│   ├── Ingest/
│   │   └── upload.py               # Parses CSV output and writes to Neo4j
│   ├── Compare/
│   │   ├── Analyse.py              # Sibling co-occurrence, stable subgraphs
│   │   └── StructuralSimilarity.py # agnostic_distance (Hungarian matching)
│   ├── Evaluate/
│   │   └── Evaluator.py            # Recall / precision / F1
│   ├── BulkGenerate.py             # Run all models × N runs in parallel
│   ├── BulkUpload.py               # Re-upload existing JSONs to Neo4j
│   └── SummariseMetrics.py         # Extract metrics from Neo4j → CSV
│
├── analysis/
│   ├── consensus_threshold/        # τ sweep analysis and plots
│   └── summary_table/              # Marginal means table, consensus, pairwise edit
│
├── data/
│   ├── Reference/
│   │   └── Games.csv               # 42 Nikoli games (ground truth)
│   └── Auto/
│       ├── model_averages.csv      # Per-model averages across all experiments
│       ├── subgraph_stats.csv      # Stable subgraph coverage stats
│       └── <experiment_name>/      # Per-experiment JSON runs and output CSVs
│
├── requirements.txt
└── .env                            # API keys and Neo4j credentials (not committed)
```

---

## Experiment Naming Convention

Experiments in this study follow the pattern `Comb_<content>_<prompt>_<temp>_<hash>`:

| Segment | Values | Meaning |
|---|---|---|
| `content` | `List` / `Rules` | Game titles only, or game rules PDF supplied |
| `prompt` | `Basic` / `SpecifyEx` / `SpecifyExCats` | Taxonomy prompt variant |
| `temp` | `T0` / `T1` | LLM temperature (0 = deterministic, 1 = default) |
| `hash` | e.g. `00654f` | Short identifier for the experiment configuration |

Example: `Comb_List_SpecifyExCats_T0_00654f`
=======
Python-Neo4j pipeline for generation and evaluation of LLM taxonomies as knowledge graphs Graph Analysis of LLM Taxonomies (GALT)
>>>>>>> origin/main
