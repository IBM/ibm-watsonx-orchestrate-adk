# Local Memory SDK Agent

This example is a custom LangGraph agent that uses the published
`ibm-watsonx-orchestrate-sdk` package to read and write memory through
`wxo-server`.

## What It Demonstrates

- request-scoped `execution_context` coming from TRM
- `Client(execution_context=execution_context)` for `runs-on`
- `client.memory.search(...)`
- `client.memory.add_messages(...)`

## Package Source

The example uses the published TestPyPI wheel directly from
`requirements.txt` and `config.yaml`. It does not rely on a vendored local
SDK wheel.

## Standard Lima Flow

1. Install the matching TestPyPI prerelease and start the standard developer edition stack:

```bash
pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ibm-watsonx-orchestrate==2.7.0.dev6291
orchestrate server start -e .env
orchestrate env activate local --registry testpypi --test-package-version-override 2.7.0.dev6291
```

2. Ensure the runtime stack provides:

```text
WXO_API_PROXY_URL=http://wxo-server:4321/api/v1
DEPLOYMENT_PLATFORM=lite-laptop
```

3. Import the example agent:

```bash
orchestrate agents import --experimental-package-root examples/custom_agents/local_memory_sdk_agent
```

4. Validate with a two-turn chat:

```bash
./.venv/bin/orchestrate chat ask --agent-name local_memory_sdk_agent
```

Then send:

- `My name is Suyash`
- `What is my name?`

The second turn should retrieve the remembered fact through the SDK memory
surface.

## Files

- `agent.py`: LangGraph entrypoint
- `agent.yaml`: custom-agent manifest
- `config.yaml`: package metadata
- `requirements.txt`: published SDK wheel plus LangGraph dependencies
- `seed_memory.json`: optional sample memory payload
