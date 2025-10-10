### 📊 Evaluation File Structure

The `analyze` command supports both **single-run** and **multi-run** evaluations. It automatically determines the mode by examining the filenames in the target directory.

---

#### 🧪 Single-Run Evaluations

For single-run evaluations, the following files are generated:

- `<DATASET>.messages.json` — Raw messages exchanged during the simulation.  
- `<DATASET>.messages.analyze.json` — Annotated analysis, including mistakes and step-by-step comparison to ground truth.  
- `<DATASET>.metrics.json` — Metrics summary for that specific test case.

---

#### 🔁 Multi-Run Evaluations

When the `n_runs` parameter is set to more than 1, separate files are generated for each run using a **run-indexed naming pattern**:

- `<DATASET>.run<runN>.messages.json`  
- `<DATASET>.run<runN>.messages.analyze.json`  
- `<DATASET>.run<runN>.metrics.json`

Here, `<runN>` represents the run number (for example, `run1`, `run2`, and so on).

---

#### 🧠 Auto-Detection

The `analyze` command dynamically determines whether a directory contains single-run or multi-run results based on the **file name structure**:

- If files with `.runN.` are found, it treats the evaluation as multi-run and aggregates results across runs.  
- If no `.runN.` files are found, it falls back to single-run analysis.

This allows you to analyze both modern and legacy evaluation outputs without renaming files.


### how to run analyze command example

1. open a terminal and maximize the window width & length on the screen

2. Option1: Run the following command: `orchestrate evaluations analyze -d ./examples/evaluations/analysis/ -e .env_file`

3. Option2: Run the command with tools directory to perform additional analysis with tools:
`orchestrate evaluations analyze -d ./examples/evaluations/analysis/ -e env.lite -t ./examples/evaluations/analysis/tools.py`
🚨 Note: we expect `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` to be part of the environment variables or specified in .env_file. 

**Note:** To run **multi-run analysis**, use the following command::  
`orchestrate evaluations analyze -d examples/evaluations/analysis/multi_run_example -t examples/evaluations/analysis/multi_run_example/tools.py`

#### Using IBM Cloud Pak for Data (CPD)
For running analyze/evaluate flows against CPD (with or without IFM), see:
- examples/evaluations/cpd/README.md
