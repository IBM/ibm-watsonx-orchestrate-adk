# Installation Guide

This guide will help you set up Knowledge to work with the banking agent demonstration.


## Setup Steps

### 1. Setup a local OpenSearch instance

In a terminal window, navigate to the [knowledge](../../toolkits/banking_mcp_server/knowledge/) directory. 

Create a `.env` file with the following entry:

```
OPENSEARCH_PASSWORD=<the OpenSearch admin password you wish to use>
```

And then do:

```bash
docker compose up
```

If your system has podman installed, you can also do `podman compose up`.

If your system has rancher installed, you need to select the `dockerd(moby)` container engine in order to use `docker compose up`.

Note: Please ensure you are not using Orchestrate Developer Edtition docker context for this step. You can check your current context by running `docker context ls`. If you are using Orchestrate Developer Edition docker context, switch to the default context by running `docker context use default`.

### 2. Verify the local OpenSearch instance

In a new terminal window, run the curl command:

```bash
curl https://localhost:9200 -ku admin:"<your OpenSearch admin password>"
```

A response like below should show up:

```
{
  "name" : "opensearch-node1",
  "cluster_name" : "opensearch-cluster",
  "cluster_uuid" : "m2xUjNuOSiiyS52aw8EIKg",
  "version" : {
    "distribution" : "opensearch",
    "number" : "3.4.0",
    "build_type" : "tar",
    "build_hash" : "00336141f90b2456d7aa35e9052fd6baf7147423",
    "build_date" : "2025-12-15T21:42:54.481067826Z",
    "build_snapshot" : false,
    "lucene_version" : "10.3.2",
    "minimum_wire_compatibility_version" : "2.19.0",
    "minimum_index_compatibility_version" : "2.0.0"
  },
  "tagline" : "The OpenSearch Project: https://opensearch.org/"
}
```

### 3. Install Knowledge Dependencies

In a new terminal window, navigate to the [knowledge](../../toolkits/banking_mcp_server/knowledge/) directory:

```bash
cd knowledge
uv sync
```

### 4. Register the machine learning model and create the pipelines

In the same terminal window, do:

```bash
uv run --env-file=.env register_model_and_create_pipelines.py
```

Wait until you see the message: `The model was registered and the pipelines were created successfully`

### 5. Create the vector index

In the same terminal window, do:

```bash
uv run --env-file=.env create_vector_index.py
```

By default, this will create a vector index named `knowledge_vector_index`. You can change the name by setting the environment variable `INDEX_NAME` to a different value.

### 6. Ingest document

This repository comes with 2 PDF files that has the example knowledge content for the banking agent. 

In the same terminal window, do:

```bash
uv run --env-file=.env ingest_document.py faq/Checking_Savings_Account_FAQ.pdf 
uv run --env-file=.env ingest_document.py faq/Mortgage_FAQ.pdf
```

Note, depending on the available memory resource in your system, you may get an error like this:

```
Status Code: 429
Reason: Too Many Requests
Response Content: {"error":{"root_cause":[{"type":"circuit_breaking_exception","reason":"Memory Circuit Breaker is open, please check your resources!","bytes_wanted":0,"bytes_limit":0,"durability":"TRANSIENT"}],"type":"circuit_breaking_exception","reason":"Memory Circuit Breaker is open, please check your resources!","bytes_wanted":0,"bytes_limit":0,"durability":"TRANSIENT"},"status":429
```

The `ingest_document.py` script will automatically retry to remediate it. If the issue persists, please check available memory in your system, and close unused applications to free up memory and try again.

### 7. Restart the MCP Server

If the MCP server was started, stop it. 

In the same terminal window, from the root directory of the repository:

```bash
export OPENSEARCH_PASSWORD=<your OpenSearch admin password>
# Start the MCP server in development mode
npm run dev
```

The server will start on `http://localhost:3004` by default. You should see:
```
Banking MCP server listening on port 3004
```

Then in the agent chat window, you can ask questions such as `What's the fee if I exceed my monthly transfer limit?`, the answer will be grounded on the example knowledge content in the vector store (OpenSearch).