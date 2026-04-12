# Installation Guide

This guide will help you set up BYO (Bring Your Own) Knowledge to work with the banking agent demonstration.

Before following the setup steps in this installation guide, you should have already had a remote Opensearch instance setup and configured similar to the steps 4-6 as in the [Setting Up Knowledge](./SettingUpKnowledge.md) guide.

## Setup Steps

### 1. Find the required information in the BYO Knowledge instance 

In your BYO Knowledge instance, find the following information:

- the endpoint of the BYO OpenSearch instance
- the port of the BYO OpenSearch instance
- the username of the BYO OpenSearch instance
- the password of the BYO OpenSearch instance
- the name of the vector index that has the knowledge
- the name of the field in the index that has the knowledge title
- the name of the field in the index that has the knowledge content
- the name of the field in the index that has the knowledge URL (optional)
- the name of the field in the index that has the vectorized knowledge content

### 2. Create a custom query body to search the BYO Knowledge instance

An example query body looks like this: `{"query":{"neural":{"passage_embedding":{"query_text":"$QUERY","k":10}}}}`

In this example, `passage_embedding` is the name of the index field that has the vectorized knowledge content. If your BYO Knowledge uses a different name, you should use the actual name in your query body.

`$QUERY` is a reserved word supported by the example Knowledge tool, it will be replaced by the actual query text that the tool receives from the agent at runtime.

Here are other reserved words that are supported in the custom query body by the example Knowledge tool:
- `$BODY_FIELD` - Will be replaced with the value of the `OPENSEARCH_FIELD_BODY` environment variable
- `$TITLE_FIELD` - Will be replaced with the value of the `OPENSEARCH_FIELD_TITLE` environment variable

For more details about the supported syntax of the query body, please refer to the [OpenSearch Documentation](https://opensearch.org/docs/latest/)

### 3. Set the environment variables and start the MCP Server

If the MCP server was started, stop it. 

In a terminal window, from the root directory of the repository:

```bash
export OPENSEARCH_ENDPOINT=<the endpoint of the BYO OpenSearch instance>
export OPENSEARCH_PORT=<the port of the BYO OpenSearch instance>
export OPENSEARCH_USERNAME=<the username of the BYO OpenSearch instance>
export OPENSEARCH_PASSWORD=<the password of the BYO OpenSearch instance>

export INDEX_NAME=<the name of the vector index that has the knowledge>
export OPENSEARCH_FIELD_TITLE=<the name of the field in the index that has the knowledge title>
export OPENSEARCH_FIELD_BODY=<the name of the field in the index that has the knowledge content>
export OPENSEARCH_FIELD_URL=<the name of the field in the index that has the knowledge URL, optional>

export OPENSEARCH_QUERY_BODY=<the custom query body that the knowledge tool should use to search the BYO Knowledge>

# Start the MCP server in development mode
npm run dev
```

The server will start on `http://localhost:3004` by default. You should see:
```
Banking MCP server listening on port 3004
```

Then in the agent chat window, you can ask questions such as `What's the fee if I exceed my monthly transfer limit?`, the answer will be grounded on the example knowledge content in the vector store (OpenSearch).

