# Worked Examples — watsonx Orchestrate

Complete end-to-end examples. Each shows the task, the files produced, and what to run.
Source directory: `wxo-clients/examples/` in the ADK repo.

## Contents
- [Example 1: Simple tool agent (healthcare claims)](#example-1-simple-tool-agent)
- [Example 2: Knowledge base agent](#example-2-knowledge-base-agent)
- [Example 3: Multi-agent collaborator chain](#example-3-multi-agent-collaborator-chain)
- [Example 4: Conditional-branch flow](#example-4-conditional-branch-flow)
- [Example 5: foreach flow (bulk operations)](#example-5-foreach-flow)
- [Example 6: Document extraction flow](#example-6-document-extraction-flow)

---

## Example 1: Simple Tool Agent

**Task:** An agent that answers healthcare questions using three Python tools (benefits, claims, provider search). One collaborator agent handles ServiceNow tickets.

### `tools/get_my_claims.py`
```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool
def get_my_claims():
    """Retrieve submitted claims with status, amounts, and services.

    Returns:
        list: Claims records with claimId, claimStatus, amountClaimed, amountApproved, provider, services.
    """
    return [
        {"claimId": "CLM1234567", "claimStatus": "Processed",
         "amountClaimed": 150.00, "amountApproved": 120.00,
         "provider": {"name": "Healthcare Clinic ABC", "providerType": "Clinic"},
         "services": [{"description": "General Consultation", "amount": 100.00}]},
    ]
```

### `tools/search_healthcare_providers.py`
```python
from typing import List
from enum import Enum
import requests
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool

class HealthcareSpeciality(str, Enum):
    GENERAL_MEDICINE = 'General Medicine'
    CARDIOLOGY = 'Cardiology'
    ENT = 'Ear, Nose and Throat'

class HealthcareProvider(BaseModel):
    name: str = Field(description="Provider name")
    specialty: HealthcareSpeciality = Field(description="Medical specialty")
    address: str = Field(description="Provider address")

@tool
def search_healthcare_providers(
    location: str,
    specialty: HealthcareSpeciality = HealthcareSpeciality.GENERAL_MEDICINE
) -> List[HealthcareProvider]:
    """Search for healthcare providers near a location.

    Args:
        location (str): City, state, or zip code.
        specialty (HealthcareSpeciality): Medical specialty to filter by.
    Returns:
        List[HealthcareProvider]: Matching providers.
    """
    resp = requests.get("https://my-provider-api.example.com/providers",
                        params={"location": location, "speciality": specialty})
    resp.raise_for_status()
    return resp.json()["providers"]
```

### `agents/customer_care_agent.yaml`
```yaml
spec_version: v1
kind: native
name: customer_care_agent
description: >
  Answers healthcare benefit and claims questions, and searches for nearby providers.
  Use when a user asks about insurance, claims status, or finding a doctor.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic
instructions: >
  Use search_healthcare_providers to find providers. Format multiple results as a
  markdown table. Use get_my_claims for claims status — respond in a direct tone,
  do not negotiate prices, format as a markdown table.
tools:
  - get_my_claims
  - search_healthcare_providers
collaborators:
  - service_now_agent
starter_prompts:
  prompts:
    - id: p1
      title: Check my claims
      prompt: What are my open medical claims?
    - id: p2
      title: Find a cardiologist
      prompt: Find a cardiologist near Chicago, IL
welcome_content:
  welcome_message: Healthcare Assistant
  description: Ask me about your claims, benefits, or nearby providers.
```

### `import-all.sh`
```bash
#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# tools (no credentials needed for these)
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/get_my_claims.py"
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/search_healthcare_providers.py"

# collaborator first, then orchestrator
orchestrate agents import -f "${SCRIPT_DIR}/agents/service_now_agent.yaml"
orchestrate agents import -f "${SCRIPT_DIR}/agents/customer_care_agent.yaml"
```

Source: [`examples/agent_builder/customer_care/`](../../examples/agent_builder/customer_care/)

---

## Example 2: Knowledge Base Agent

**Task:** An agent grounded in IBM history documents (PDF), also able to look up stock prices via a tool.

### `knowledge_base/ibm_kb.yaml`
```yaml
spec_version: v1
kind: knowledge_base
name: ibm_knowledge_base
description: General information about IBM and its history
documents:
  - path: IBM_wikipedia.pdf
  - path: history_of_ibm.pdf
vector_index:
  embeddings_model_name: ibm/slate-125m-english-rtrvr-v2
```

### `tools/get_stock_price.py`
```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool
def get_stock_price(stock_symbol_list: list[str]) -> dict:
    """Retrieve current stock prices.

    Args:
        stock_symbol_list (list[str]): List of stock ticker symbols.
    Returns:
        dict: Mapping of symbol to price.
    """
    prices = {"IBM": 185.50, "MSFT": 420.00, "AAPL": 210.00}
    return {s: prices[s] for s in stock_symbol_list if s in prices}
```

### `agents/ibm_agent.yaml`
```yaml
spec_version: v1
kind: native
name: ibm_agent
description: Answers questions about IBM history and stock prices.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic
instructions: >
  Answer IBM history questions using the knowledge base. For stock prices,
  call get_stock_price with the ticker symbol.
knowledge_base:
  - ibm_knowledge_base
tools:
  - get_stock_price
starter_prompts:
  prompts:
    - id: p1
      title: IBM founding
      prompt: When was IBM founded and what was its original name?
    - id: p2
      title: Stock price
      prompt: What is IBM's current stock price?
welcome_content:
  welcome_message: IBM Knowledge Agent
  description: Ask me anything about IBM history or its stock price.
```

### `import-all.sh`
```bash
#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate knowledge-bases import -f "${SCRIPT_DIR}/knowledge_base/ibm_kb.yaml"
# wait for indexing: orchestrate knowledge-bases status -n ibm_knowledge_base
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/get_stock_price.py"
orchestrate agents import -f "${SCRIPT_DIR}/agents/ibm_agent.yaml"
```

Source: [`examples/agent_builder/ibm_knowledge/`](../../examples/agent_builder/ibm_knowledge/)

---

## Example 3: Multi-Agent Collaborator Chain

**Task:** An orchestrator agent fans out to three specialist agents (weather, population, founding date), then aggregates results via a fourth agent, all wired through a flow.

**Architecture:**
```
get_city_facts_agent (orchestrator)
  └── collaborator_agents_flow (@flow)
        ├── aflow.agent → weather_agent
        ├── aflow.agent → population_agent
        ├── aflow.agent → city_founding_date_agent
        └── aflow.agent → aggregate_agent  ← combines all three results
```

### `agents/weather_agent.yaml` (collaborator — import first)
```yaml
spec_version: v1
kind: native
name: weather_agent
description: Fetches real-time weather data for a city.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic
instructions: >
  Call get_weather_data with the provided city. Return wind_speed, temperature, current_weather.
tools:
  - get_weather_data
```

### `tools/collaborator_agents_flow.py` (the coordinating flow)
```python
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END

class FlowInput(BaseModel):
    city: str = Field(description="City name")

class WeatherData(BaseModel):
    wind_speed: float
    temperature: float
    current_weather: str

class PopulationData(BaseModel):
    population: str
    coordinates: str

class CityFoundingDate(BaseModel):
    founding_date: str

class FlowOutput(BaseModel):
    result: str = Field(description="City summary")

class AllFacts(BaseModel):
    wind_speed: float
    temperature: float
    current_weather: str
    population: str
    coordinates: str
    city: str
    founding_date: str

@flow(name="collaborator_agents_flow", input_schema=FlowInput, output_schema=FlowOutput)
def build_collaborator_agents_flow(aflow: Flow) -> Flow:
    founding = aflow.agent(name="ask_founding", agent="city_founding_date_agent",
                           message="Give the founding date of the provided city",
                           input_schema=FlowInput, output_schema=CityFoundingDate)
    weather  = aflow.agent(name="ask_weather",  agent="weather_agent",
                           message="Give real-time weather for the provided city",
                           input_schema=FlowInput, output_schema=WeatherData)
    pop      = aflow.agent(name="ask_pop",      agent="population_agent",
                           message="Give population and coordinates for the provided city",
                           input_schema=FlowInput, output_schema=PopulationData)
    aggregate = aflow.agent(name="ask_aggregate", agent="aggregate_agent",
                            message="Invoke aggregate_data with the provided facts",
                            input_schema=AllFacts, output_schema=FlowOutput)
    aflow.sequence(START, founding, weather, pop, aggregate, END)
    return aflow
```

### `agents/get_city_facts_agent.yaml` (orchestrator — import last)
```yaml
spec_version: v1
kind: native
name: get_city_facts_agent
description: Gathers weather, population, and founding date for a city.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic
instructions: >
  Accept a city name. Call collaborator_agents_flow to gather all city facts.
  Valid cities: San Jose CA, Fremont, New York, Los Angeles.
tools:
  - collaborator_agents_flow
starter_prompts:
  prompts:
    - id: p1
      title: City facts
      prompt: Tell me about New York
welcome_content:
  welcome_message: City Facts Agent
  description: Ask me about weather, population, or history of a city.
```

### `import-all.sh`
```bash
#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# leaf tools first
for t in get_weather_data.py get_population_data.py get_city_founding_date.py aggregate_data.py; do
  orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/${t}"
done

# specialist agents (collaborators)
for a in weather_agent.yaml population_agent.yaml city_founding_date_agent.yaml aggregate_agent.yaml; do
  orchestrate agents import -f "${SCRIPT_DIR}/agents/${a}"
done

# coordinating flow, then orchestrator
orchestrate tools import -k flow -f "${SCRIPT_DIR}/tools/collaborator_agents_flow.py"
orchestrate agents import -f "${SCRIPT_DIR}/agents/get_city_facts_agent.yaml"
```

Source: [`examples/flow_builder/collaborator_agents/`](../../examples/flow_builder/collaborator_agents/)

---

## Example 4: Conditional-Branch Flow

**Task:** Route to different tool nodes based on a runtime input value (`conditions()` branch).

```python
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END, Branch

class Pet(BaseModel):
    kind: str = Field(description="Type of pet: dog or cat")

class PetFacts(BaseModel):
    facts: list[str] = Field(description="Facts about the pet")

@flow(name="get_pet_facts", input_schema=Pet, output_schema=PetFacts)
def build_get_pet_facts_flow(aflow: Flow) -> Flow:
    dog_node = aflow.tool("getDogFact")   # reference an already-imported tool by name
    cat_node = aflow.tool("getCatFact")

    router: Branch = aflow.conditions()
    router.condition(expression="flow.input.kind.strip().lower() == 'dog'", to_node=dog_node) \
          .condition(expression="flow.input.kind.strip().lower() == 'cat'", to_node=cat_node) \
          .condition(default=True, to_node=dog_node)   # fallback

    aflow.edge(START, router)
    aflow.edge(dog_node, END)
    aflow.edge(cat_node, END)
    return aflow
```

**Key points:**
- `aflow.tool("name_string")` references an already-imported tool by name (no local import needed).
- Both branch endpoints wire to `END` independently.
- `default=True` is the catch-all — always include one.

Source: [`examples/flow_builder/get_pet_facts_if_else/`](../../examples/flow_builder/get_pet_facts_if_else/)

---

## Example 5: `foreach` Flow

**Task:** Fetch a list of customers, then iterate and send an invitation email to each one sequentially.

```python
from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.flow_builder.types import ForeachPolicy
# assume get_emails_from_customer and send_invitation_email are imported @tool functions

class CustomerName(BaseModel):
    name: str = Field(description="Customer search name")

class CustomerRecord(BaseModel):
    name: str
    email: str

@flow(name="send_invitations", input_schema=CustomerName)
def build_send_invitations(aflow: Flow) -> Flow:
    # Step 1 — get the list
    get_list = aflow.tool(get_emails_from_customer)

    # Step 2 — iterate: item_schema is the type of each element in the list
    foreach = aflow.foreach(item_schema=CustomerRecord).policy(kind=ForeachPolicy.SEQUENTIAL)
    send = foreach.tool(send_invitation_email)
    foreach.sequence(START, send, END)

    aflow.edge(START, get_list)
    aflow.edge(get_list, foreach)
    aflow.edge(foreach, END)
    return aflow
```

**Key points:**
- `aflow.foreach(item_schema=T)` creates a subflow; add nodes **on the foreach subflow**, not the parent.
- `ForeachPolicy.PARALLEL` runs all iterations concurrently (no user-activity nodes inside).
- Inside the foreach subflow, the current item is at `parent._current_item`.

Source: [`examples/flow_builder/foreach_email/`](../../examples/flow_builder/foreach_email/)

---

## Example 6: Document Extraction Flow

**Task:** User uploads a contract PDF; the flow extracts structured fields (buyer, seller, date, contract type).

```python
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.flow_builder.types import DocExtConfigField, DocumentProcessingCommonInput

class ContractFields(BaseModel):
    buyer: DocExtConfigField = Field(default=DocExtConfigField(
        name="Buyer", field_name="buyer"))
    seller: DocExtConfigField = Field(default=DocExtConfigField(
        name="Seller", field_name="seller"))
    agreement_date: DocExtConfigField = Field(default=DocExtConfigField(
        name="Agreement Date", field_name="agreement_date", type="date"))
    contract_type: DocExtConfigField = Field(default=DocExtConfigField(
        name="Contract Type", field_name="contract_type", type="string",
        description="Type of contract between buyer and seller."))

@flow(name="extract_contract_fields",
      description="Extract structured fields from a contract PDF.",
      input_schema=DocumentProcessingCommonInput)
def build_extract_contract(aflow: Flow) -> Flow:
    # aflow.docext returns (node, OutputSchema)
    # OutputSchema can be passed as input_schema to downstream nodes
    node, _OutputSchema = aflow.docext(
        name="contract_extractor",
        display_name="Extract Contract Fields",
        description="Extracts buyer, seller, date, and contract type from a contract",
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        fields=ContractFields(),
        field_extraction_method="layout",  # required for date/typed fields
    )
    aflow.sequence(START, node, END)
    return aflow
```

**Agent YAML** (the agent just invokes the flow — it does NOT ask the user for a file first):
```yaml
spec_version: v1
kind: native
name: contract_agent
description: Extracts structured data from uploaded contract documents.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic
instructions: >
  When the user wants to process a contract, immediately invoke extract_contract_fields.
  Do NOT ask the user to upload the file first — the flow handles the upload prompt itself.
tools:
  - extract_contract_fields
starter_prompts:
  prompts:
    - id: p1
      title: Extract contract
      prompt: Extract fields from my contract
welcome_content:
  welcome_message: Contract Extractor
  description: Upload a contract PDF and I will extract the key fields.
```

**Key points:**
- `DocumentProcessingCommonInput` is the standard input schema for all document flows — do not define your own.
- The `docproc`/`docext` node handles the file upload prompt; the agent must **not** prompt for a file separately.
- `field_extraction_method="layout"` is required when using typed fields (`type="date"`, `type="number"`), tables, or `available_options`.

Source: [`examples/flow_builder/document_extractor/`](../../examples/flow_builder/document_extractor/)
