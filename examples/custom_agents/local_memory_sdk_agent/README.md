# Local Memory SDK Agent

This example is a custom LangGraph agent that uses the published
`ibm-watsonx-orchestrate-sdk` package to read and write memory through
`wxo-server`.

For the current runs-on agent pattern, SDK memory APIs, valid
`memory_type` values, scoping rules, and copy-paste examples, see
[SDK_MEMORY_REFERENCE.md](/Users/suyash/Documents/GitHub/wxo-clients/examples/custom_agents/local_memory_sdk_agent/SDK_MEMORY_REFERENCE.md).

## What It Demonstrates

- request-scoped `execution_context` coming from TRM
- `Client(execution_context=execution_context)` for `runs-on`
- `client.memory.search(...)`
- `client.memory.add_messages(...)`

## Package Source

The example uses the published TestPyPI wheel directly from
`requirements.txt` and `config.yaml`. It does not rely on a vendored local
SDK wheel.

## Standard Flow

1. Install the matching TestPyPI prerelease and start the standard developer edition stack:

```bash
pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ibm-watsonx-orchestrate==2.9.0.dev6437
orchestrate server start -e .env
orchestrate env activate local --registry testpypi --test-package-version-override 2.9.0.dev6437
```

2. Ensure the runtime stack provides the correct runs-on API base through
`execution_context.api_proxy_url` or `WXO_API_PROXY_URL`.

The SDK uses that value as-is. It does not append instance or version
segments for you.

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
