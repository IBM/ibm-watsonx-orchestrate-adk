# Server Start Command

The `orchestrate server start` command is used to download and run the services that compose the Watson Orchestrate service. 

## Prerequisites
- You must have `docker` and `docker compose` installed on your system.  This can be anything
compatible with docker such as Rancher, Podman, etc.

## Watson Orchestrate Server Components
- There is a set of services that make up the Watson Orchestrate application
- Each service specifies a Docker image to download and run on your local machine
- Environment variables are set to configure each service
- Ports are mapped to make services accessible
- Volumes are mounted to persist data
- The wxo-server and wxo-server-worker are the core services
- Supporting services like Redis, Postgres, Minio are also started
- The `orchestrate server start` command downloads the images and starts all the containers
- The `orchestrate server stop` and `orchestrate server reset` commands will stop and delete these components

## 5. Accessing Services Locally
After issuing the `orchestrate server start` command, the following services will be accessible:

- **UI**: [http://localhost:3000/chat-lite](http://localhost:3000/chat-lite) 
- **OpenAPI Docs**: [http://localhost:4321/docs](http://localhost:4321/docs)
- **API Base URL**: [http://localhost:4321/api/v1](http://localhost:4321/api/v1)
- **Flower (Task Management)**: [http://localhost:5555/tasks](http://localhost:5555/tasks)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)
- **PostgreSQL DB**: `postgresql://localhost:5432/postgres`


## Requirements

The following environment variables must be set before running the command:

- `DOCKER_IAM_KEY`: The IAM API key for authenticating with the Docker registry. This can be obtained from your IBM Cloud account at https://cloud.ibm.com. Go to "Manage" > "Access (IAM)" > "API keys" and create a new key.

- `WATSONX_SPACE_ID`: The ID of your Watson X space. This can be found in your Watson X account at https://cloud.ibm.com. Go to your Watson X space and copy the "Space ID" value. 

- `WATSONX_APIKEY`: The API key for your Watson X service. This can be created in your Watson X account at https://cloud.ibm.com. Go to "Service credentials" and create a new credential.

You should set these in a environment file and refer to that with the start command.
For example:
- `orchestrate server start --env-file=./env.lite`

Where env.lite contains:
```
DOCKER_IAM_KEY=your IBM key from cloud.ibm.com
WATSONX_SPACE_ID=your watsonx space id 
WATSONX_APIKEY=your watsonx api key
```


## Other Server and Related Commands

- `orchestrate server stop`: Stops the running server and all ibm-watsonx-orchestrate docker images 
- `orchestrate server reset`: Stops the server, stops all ibm-watsonx-orchestrate docker images, and resets all data volumes
- `orchestrate server logs`: Displays the server logs
- `orchestrate chat start`: Launches the UI service and the chat web UI in a browser
- `orchestrate chat start --agent-name=my_new_name`: Launches the UI service and the chat web UI in a browser overriding the agent name to my_new_name

## Configuration

The `docker/default.env` file contains additional configuration variables that can be overridden if needed. 
One reason to do this is if you wish to use different AI models for different orchestrate tasks.
Here is a brief description of the configuration variables that can be overridden:

- `REGISTRY_URL`: The URL of the Docker registry (default: us.icr.io)
- `JWT_SECRET`: Secret key for JWT token signing. Can be generated with Python secrets module. 
- `POSTGRES_URL`: URL for Postgres database connection
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`: Redis URL for Celery task queue
- `FLOWER_URL`: URL for Flower task monitoring dashboard 
- `STORAGE_S3_*`: Configuration for S3 compatible object storage
- `ASSISTANT_*`: Configuration for Watson Assistant
- `ROUTING_*`: Configuration for routing requests
- `WXAI_PROJECT_ID`: Project ID for Watson X AI
- `EVENT_BROKER_URL`: Redis URL for event streaming  
- `DB_ENCRYPTION_KEY`: Encryption key for sensitive data in DB
- `BASE_URL`: Base URL the server is accessible from
- `SERVER_TYPE`: Server mode (CELERY for async workers)
- `LANGFUSE_*`: Configuration for Langfuse service
- `CELERY_*`: Celery worker settings
- `DEFAULT_SETTINGS` / `*_PROMPTS_DIR`: Paths to various config files

## Troubleshot

### server start fails with `pull access denied`
1). try to login manually `docker login -u iamapikey -p APIKEY  us.icr.io` and verify indeed the apikey gives the access.
if login fails, reach out to slack `#wxo-agent-buider`   
2). if 1) is successful and server still fails to start , try to locate `~/.docker/config.json`. if the file does not exist, run `touch ~/.docker/config.json` to create the file. 
Add the following section:    
```
{
        "auths": {
                "us.icr.io": {
                        "auth": BASE64_ENCODED_CRED
                }
        }
}
```
Note: BASE64_ENCODED_CRED should be based64 encoded string of `iamapikey:APIKEY`.
