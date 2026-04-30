# AgentOps Integration Testing Guide

## Overview
This guide provides testing procedures for the AgentOps integration with watsonx Orchestrate ADK after upgrading to the latest agentops version.

## Environment Setup
```bash
# Clone wxo-clients repo
git clone git@github.ibm.com:WatsonOrchestrate/wxo-clients.git 
cd wxo-clients

# update pyproject.toml in wxo-clients to the newest version of agentops
agentops = [
    "ibm_watsonx_orchestrate_evaluation_framework==<version>",
] 
 
# Set up repo as instructed in README, e.g. installing dependenices
pip install -e ".[dev]" 
```
 
Start Orchestrate Server (if testing locally)
```bash
# Start with Langfuse telemetry enabled
orchestrate server start --env-file .env -l
```

Ensure .env file has been properly populated.\
Usually, `WATSONX_APIKEY, WATSONX_SPACE_ID` or `WO_INSTANCE, WO_API_KEY` are expected
to be part of the environment variables or specified in the .env file.

---

## Testing functionality
Ensure you're in the `wxo-clients` directory when running the commands.\
Ensure a `.env` file exists in the directory and is properly populated with the required credentials.
A test automation script is available at `examples/evaluations/run_all_tests.py` to run all tests sequentially. 
Note that test results require manual check to verify they are working properly.

### 1. Unit Tests

```bash
pytest tests/cli/commands/evaluations/
```

**Expected Result:** All tests should pass without being skipped.

**If any tests are skipped or fail:** Find the source of failure and fix them.

---

### 2. Test Basic Orchestrate Commands

```bash
orchestrate evaluations --help
orchestrate evaluations evaluate --help
orchestrate evaluations record --help
orchestrate evaluations generate --help
orchestrate evaluations analyze --help
orchestrate evaluations validate-external --help
orchestrate evaluations quick-eval --help
orchestrate evaluations red-teaming --help
```

**Expected Result:** All commands should display help text without errors.

---
### 3. Evaluation (Legacy Mode)

**Location** `examples/evaluations/evaluate/README.md`

**Steps** 
```bash
# import all tools/agents
# update models for agents if needed
bash examples/evaluations/evaluate/import-all.sh

# run evaluation
orchestrate evaluations evaluate \
  -p ./examples/evaluations/evaluate/ \
  -o ./output/eval \
  -e .env

# Optionally, can also run with environment manager instead, which handles agents/tools imports
orchestrate evaluations evaluate \
--env-manager-path examples/evaluations/environment_manager/env_manager.yaml \
--output-dir ./output/eval
```
 

**Expected result/log output:**

```log
[INFO] - Using test paths: ['./examples/evaluations/evaluate/']
[INFO] - Using output directory: ./debug
[INFO]: agentops.arg_configs Default provider set to 'gateway' based on USE_GATEWAY_MODEL_PROVIDER environment variable 
[INFO]: agentops.resource_map ✔ ResourceMap initialized successfully 
Found 2 files in './examples/evaluations/evaluate/' (non-recursive)
Discovered 2 test cases in total
[INFO]: agentops.runner Running test case: data_complex 
[INFO]: agentops.runner Running test case: data_simple 
...
                                            Agent Metrics                                             
╭────────┬──────┬────────┬────────┬───────┬────────┬───────┬────────┬───────┬────────┬───────┬────────╮
│        │      │        │        │       │        │       │        │       │        │       │ Avg    │
│        │      │        │        │ Total │ Tool   │ Tool  │ Agent  │       │        │ Jour… │ Resp   │
│        │      │ Total  │ LLM    │ Tool  │ Call   │ Call  │ Routi… │ Text  │ Journ… │ Comp… │ Time   │
│ Datas… │ Runs │ Steps  │ Steps  │ Calls │ Preci… │ Reca… │ F1     │ Match │ Succe… │ %     │ (sec)  │
├────────┼──────┼────────┼────────┼───────┼────────┼───────┼────────┼───────┼────────┼───────┼────────┤
│ data_… │ 1.0  │ 11.0   │ 9.0    │ 7.0   │ 0.57   │ 1.33  │ 1.0    │ 100.… │ 0.0    │ 125.… │ 5.46   │
├────────┼──────┼────────┼────────┼───────┼────────┼───────┼────────┼───────┼────────┼───────┼────────┤
│ data_… │ 1.0  │ 22.0   │ 15.0   │ 8.0   │ 0.25   │ 1.0   │ 1.0    │ 0.0%  │ 0.0    │ 200.… │ 3.21   │
├────────┼──────┼────────┼────────┼───────┼────────┼───────┼────────┼───────┼────────┼───────┼────────┤
│ Summa… │ 1.0  │ 16.5   │ 12.0   │ 7.5   │ 0.41   │ 1.17  │ 1.0    │ 50.0% │ 0.0    │ 162.… │ 4.33   │
│ (Aver… │      │        │        │       │        │       │        │       │        │       │        │
╰────────┴──────┴────────┴────────┴───────┴────────┴───────┴────────┴───────┴────────┴───────┴────────
```

**Expected file output:**
- `output_dir/messages` contains `*.messages.json`, `*.messages.analyze.json`, `*.metrics.json`

**Expected output in Langfuse:**
- Navigate to: http://localhost:3010/project/orchestrate-lite/sessions
- Verify there are two sessions
- Verify the session IDs match the values in:
  - `output_dir/data_complex.metadata.json`
  - `output_dir/data_simple.metadata.json`

---
### 4. Evaluation (Non-Legacy Mode)

**Steps:**
```bash 
# import all agents/tools if you haven't
bash examples/evaluations/evaluate/import-all.sh
# 1. Enable non-legacy mode
export USE_LEGACY_EVAL=FALSE
# 2. Run evaluation with Langfuse
orchestrate evaluations evaluate \
  -p examples/evaluations/evaluate/data_no_summary \
  -o ./output/eval_legacy \
  -l \
  -e .env
```


**Expected result/log output:**

```log
[WARNING] - Using beta evaluation. This feature is still in beta.
[WARNING] - To use legacy evaluation, please enable it using `export USE_LEGACY_EVAL=TRUE`
[INFO] - Langfuse responded
[INFO] - Using test paths: ['examples/evaluations/evaluate/data_no_summary']
[INFO] - Using output directory: ./debug
[INFO]: agentops.arg_configs Default provider set to 'gateway' based on USE_GATEWAY_MODEL_PROVIDER 
environment variable 
[INFO]: agentops.resource_map ✔ ResourceMap initialized successfully 
Found 2 files in 'examples/evaluations/evaluate/data_no_summary' (non-recursive)
Discovered 2 test cases in total
[INFO]: agentops.runner Running test case: data_simple 
[INFO]: agentops.runner Running test case: data_complex 
...

Config and metadata saved to ./debug/2026-03-28_01-56-43
Evaluation run completed for collection default-collection:
                                          Evaluation Results                                           
╭─────┬─────┬─────┬─────┬─────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────╮
│     │     │     │     │     │ Av… │    │     │    │     │ T… │     │    │     │    │     │    │     │
│     │     │ Or… │     │     │ Ag… │    │     │    │     │ C… │     │    │     │    │     │    │     │
│     │     │ Ag… │     │     │ Re… │ T… │ Ex… │ C… │ Mi… │ w… │ To… │ T… │ To… │    │     │    │     │
│     │     │ Ro… │ To… │ LLM │ Ti… │ T… │ To… │ T… │ To… │ I… │ Ca… │ C… │ Ma… │ K… │ Se… │ T… │ Jo… │
│ Da… │ Ru… │ F1  │ St… │ St… │ (s) │ C… │ Ca… │ C… │ Ca… │ P… │ Re… │ P… │ Su… │ M… │ Ma… │ M… │ Su… │
├─────┼─────┼─────┼─────┼─────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┤
│ da… │  1  │ 1.0 │ 57… │ 49… │ 3.… │ 4… │ 2.0 │ 1… │ 1.0 │ 2… │ 0.5 │ 0… │ 0.0 │ 1… │ 1.0 │ 0… │ 0.0 │
├─────┼─────┼─────┼─────┼─────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┤
│ da… │  1  │ 1.0 │ 30… │ 23… │ 2.… │ 1… │ 5.0 │ 2… │ 3.0 │ 1… │ 0.4 │ 0… │ 0.0 │ 1… │ 1.0 │ 0… │ 0.0 │
╰─────┴─────┴─────┴─────┴─────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────╯
 - http://localhost:3010/project/orchestrate-lite/sessions/<session_id>
 - http://localhost:3010/project/orchestrate-lite/sessions/<session_id>
```
 
**Expected output in Langfuse:**
- Navigate to: http://localhost:3010/project/orchestrate-lite/sessions
- Verify there are two sessions
- Verify the session IDs match the values in:
  - `output_dir/eval_legacy/data_complex.metadata.json`
  - `output_dir/eval_legacy/data_simple.metadata.json`
 

---
 
### 5: Evaluation with Context Variable
**Location:** `examples/evaluations/evaluate_with_context_variable/`

**Steps:**
```bash 
# 1. Import agent with context support
bash examples/evaluations/evaluate_with_context_variable/import-all.sh

# 2. Run evaluation
orchestrate evaluations evaluate \
  -p examples/evaluations/evaluate_with_context_variable/ \
  -o ./output/eval_context_var \
  -e .env
```

**Expected Output:**
```bash
[INFO] - Using test paths: ['examples/evaluations/evaluate_with_context_variable/']
[INFO] - Using output directory: ./output/eval_context_var

Config and metadata saved to ./output/eval_context_var/2026-04-01_18-23-25
Evaluation run completed for collection default-collection:
                                          Evaluation Results                                           
╭─────┬─────┬─────┬─────┬─────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────╮
│     │     │     │     │     │ Av… │    │     │    │     │ T… │     │    │     │    │     │    │     │
│     │     │ Or… │     │     │ Ag… │    │     │    │     │ C… │     │    │     │    │     │    │     │
│     │     │ Ag… │     │     │ Re… │ T… │ Ex… │ C… │ Mi… │ w… │ To… │ T… │ To… │    │     │    │     │
│     │     │ Ro… │ To… │ LLM │ Ti… │ T… │ To… │ T… │ To… │ I… │ Ca… │ C… │ Ma… │ K… │ Se… │ T… │ Jo… │
│ Da… │ Ru… │ F1  │ St… │ St… │ (s) │ C… │ Ca… │ C… │ Ca… │ P… │ Re… │ P… │ Su… │ M… │ Ma… │ M… │ Su… │
├─────┼─────┼─────┼─────┼─────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┤
│ da… │  1  │ 1.0 │ 14… │ 7.0 │ 5.… │ 6… │ 5.0 │ 1… │ 4.0 │ 5… │ 0.2 │ 0… │ 0.0 │ 0… │ 0.0 │ 0… │ 0.0 │
├─────┼─────┼─────┼─────┼─────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┤
│ da… │  1  │ 1.0 │ 19… │ 10… │ 3.… │ 8… │ 2.0 │ 2… │ 0.0 │ 0… │ 1.0 │ 0… │ 1.0 │ 0… │ 0.0 │ 1… │ 1.0 │
╰─────┴─────┴─────┴─────┴─────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────╯

```
 
- Verify that messages are generated in `output/eval_context_var`

---
 

### 6: Evaluation with File Upload 
**Location:** `examples/evaluations/evaluate_with_file_upload/`

**Steps:**
```bash 
# 1. Import agent with file upload support
bash examples/evaluations/evaluate_with_file_upload/import-all.sh

# 2. Run evaluation
orchestrate evaluations evaluate \
  -p examples/evaluations/evaluate_with_file_upload/ \
  -o ./output/file_upload_eval \
  -e .env
```

**Expected Output:**
```bash
Config and metadata saved to ./output/file_upload_eval/2026-04-01_18-50-07
Evaluation run completed for collection default-collection:
                                          Evaluation Results  
╭─────┬─────┬─────┬─────┬─────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────┬────┬─────╮
│     │     │     │     │     │ Av… │    │     │    │     │ T… │     │    │     │    │     │    │     │
│     │     │ Or… │     │     │ Ag… │    │     │    │     │ C… │     │    │     │    │     │    │     │
│     │     │ Ag… │     │     │ Re… │ T… │ Ex… │ C… │ Mi… │ w… │ To… │ T… │ To… │    │     │    │     │
│     │     │ Ro… │ To… │ LLM │ Ti… │ T… │ To… │ T… │ To… │ I… │ Ca… │ C… │ Ma… │ K… │ Se… │ T… │ Jo… │
│ Da… │ Ru… │ F1  │ St… │ St… │ (s) │ C… │ Ca… │ C… │ Ca… │ P… │ Re… │ P… │ Su… │ M… │ Ma… │ M… │ Su… │
├─────┼─────┼─────┼─────┼─────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┼────┼─────┤
│ da… │  1  │ 1.0 │ 13… │ 6.0 │ 6.… │ 4… │ 3.0 │ 3… │ 0.0 │ 1… │ 1.0 │ 0… │ 1.0 │ 0… │ 0.0 │ 1… │ 1.0 │
╰─────┴─────┴─────┴─────┴─────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────┴────┴─────╯
```
- Verify evaluation runs successfully
- Verify that messages are generated in `output/file_upload_eval`


---

### 7: Record Chat Sessions
**Purpose:** Test recording of live chat sessions for evaluation

**Steps:**
```bash 
# Start recording chat sessions
export USE_LEGACY_EVAL=TRUE
export AGENT_NAME=PLACEHOLDER_AGENT

orchestrate evaluations record \
  -o ./output/recorded_chats \
  -e .env

# Verify recording is working - choose one option:

# Option 1: Run an evaluation in a separate terminal. 
# You may use any of the previous examples.
# Open a new terminal tab and execute:
orchestrate evaluations evaluate \
  -p examples/evaluations/evaluate_with_file_upload/ \
  -o ./output/file_upload_eval \
  -e .env

# Option 2: Start an interactive chat session
orchestrate chat start
# Then select an agent and have a conversation

```

**Expected Output:**
- Verify chat recording is working
```bash
INFO: Chat recording started. Press Ctrl+C to stop.

INFO: New recording started at 2026-04-01T11:34:19.776937Z
INFO: Annotations saved to: 
test_output/recorded_chats/<uid>/<thread_id>_an
notated_data.json
INFO: Tool interactions saved to: 
test_output/recorded_chats/<uid>/<thread_id>_to
ol_calls_and_responses.json
```
- Verify chat sessions are recorded and saved to output directory

---

### 8. Generate Test Cases
**Location:** `examples/evaluations/generate/`

**Steps:**
```bash 
# 1. Import agent and tools
bash examples/evaluations/generate/import-all.sh

# 2. Generate test cases from stories
orchestrate evaluations generate \
  -s examples/evaluations/generate/stories.csv \
  -t examples/evaluations/generate/tools.py \
  -o ./output/generate \
  -e .env
```

**Expected Output:**
- Verify test cases are generated in `output/generate/` and are properly formatted. 
- There should be test cases generated for each story in `stories.csv` 
---  



### 9: Analyze Results
**Location:** `examples/evaluations/analysis/`
**Steps:**
```bash 
# Basic analysis
orchestrate evaluations analyze \
  -d examples/evaluations/analysis/ \
  -e .env

# Analysis with tool
orchestrate evaluations analyze \
  -d examples/evaluations/analysis/ \
  -e .env \
  -t examples/evaluations/analysis/tools.py

# Analysis multi run
orchestrate evaluations analyze \
  -d examples/evaluations/analysis/multi_run_example \
  -t examples/evaluations/analysis/multi_run_example/tools.py
```

**Expected Output:**
- Verify that there are rich terminal output 
with analysis summary, conversation history, tool call errors, text matches, and overall summary displayed
```bash
# partial example output
╭──────────────────────────────── 📋 Analysis Summary — data_complex ─────────────────────────────────╮
│  Type: Multi-run (2 runs)                                                                           │
│  Runs with problems: 2 / 2                                                                          │
│  Status: ❌ Problematic                                                                             │
│  Test Case Name: data_complex.run1                                                                  │
│  Expected Tool Calls: 5                                                                             │
│  Correct Tool Calls: 2                                                                              │
│  Text Match: Summary Matched                                                                        │
│  Journey Success: False                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

---
### 10: Red teaming

**Location:** `examples/evaluations/red-teaming`
**Steps:**

```bash
# Shows a list of supported attacks 
orchestrate evaluations red-teaming list

# Creates generated attacks
orchestrate evaluations red-teaming plan \
-a "Crescendo Attack, Crescendo Prompt Leakage" \
-d examples/evaluations/evaluate/data_simple.json \
-g examples/evaluations/evaluate/agent_tools \
-t hr_agent \
-o ./output/red_team

# Run and evaluate these attacks
orchestrate evaluations red-teaming run \
-a ./output/red_team \
-o ./output/red_team_run
```
**Expected Output:**
- Verify attacks are generated in `output/red_team`
- Verify attacks are ran successfully and results are generated `output/red_team_run`
--- 

### 11: Native Agent Validation
**Location**: `examples/evaluations/native_agent_validation`
**Steps**:
```bash
bash examples/evaluations/evaluate/import-all.sh 

orchestrate evaluations validate-native \
-t ./examples/evaluations/native_agent_validation/native_agent_validation.tsv \
-o ./output/native_agent_validation
```

**Expected Output:**
- Verify evaluations are ran successfully and results are generated in the output directory
---

### 12: External Agent Validation
**Location**: `examples/evaluations/external_agent_validation`
**Steps**:
```bash
orchestrate evaluations validate-external \
--tsv "./examples/evaluations/external_agent_validation/test.tsv" \
--external-agent-config \
"./examples/evaluations/external_agent_validation/sample_external_agent_config.json" \
--perf \
-o ./output/external_agent_validation
```

**Expected Output:**
- Verify evaluations are ran successfully and results are generated in the output directory
---
### 13: Quick Eval

**Location**: `examples/evaluations/quick-eval`
**Steps**:
```bash
orchestrate evaluations quick-eval \
  -p examples/evaluations/quick-eval/ \
  -o ./test_output/quick_eval \
  -e .env -t examples/evaluations/evaluate/agent_tools
```

**Expected output:**
```bash
                                   Quick Evaluation Summary Metrics                                    
╭─────────────────────┬────────────┬─────────────────────┬─────────────────────┬──────────────────────╮
│                     │            │                     │  Tool Calls Failed  │                      │
│                     │            │   Successful Tool   │    due to Schema    │  Tool Calls Failed   │
│       Dataset       │ Tool Calls │        Calls        │      Mismatch       │ due to Hallucination │
├─────────────────────┼────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
│ data_simple_no_ann… │     3      │          1          │          0          │          2           │
╰─────────────────────┴────────────┴─────────────────────┴─────────────────────┴──────────────────────╯
```
 
  

---

## Troubleshooting
 
### Missing Environment Variables
**Solution:** Check `.env` file and make sure it has all required keys

### Agent Error in Chat
Example error message:
```bash
I have encountered an error. Please try again. (Error: Error code: 403 - {'error': 
{'message': '<> error: Forbidden', 'type': None, 'param': None, 'code': None}, 'provider': '<>'})
```
**Solution:** Update agent `llm` field to a supported model and re-run import-all.sh

 
 