******************************************
## Welcome to `ibm-watsonx-orchestrate`
******************************************

`ibm-watsonx-orchestrate` is a Python SDK that allows you to build expert and orchestrator agents and interact with the 
watsonx.orchestrate service. It also provides a convenient interface for managing credentials, sending requests, and 
handling responses from the service’s APIs.

------------------------------------------

## Prerequisites

- **Python 3.11-3.13**  
  Ensure you have Python 3.11-3.13 installed.

- **Dependencies**  
  All required python dependencies will be automatically installed when you install the package. However,
  you will also need to install docker and docker compose.

------------------------------------------


### Initial setup
##### Instructions for all teams
1. Request access to the orchestrate light docker repository.
2. Make sure you have the following installed:
- docker
- docker compose
- python 3.12
3. Make sure your ssh key is uploaded to your personal github account 
   1. Run `cat ~/.ssh/id_rsa.pub` and if it returns `cat: /some/path/.ssh/id_rsa.pub: No such file or directory`, run ssh-keygen
   2. Take the contents printed out by running `cat ~/.ssh/id_rsa.pub` and upload it to [github](https://github.ibm.com/settings/keys)  
4. Run `pip install git+ssh://git@github.ibm.com/WatsonOrchestrate/wxo-clients.git`
5. Open a request on wo-tracker for access to the laptop-lite docker registry [here](https://github.ibm.com/WatsonOrchestrate/wo-tracker/issues/new?assignees=sampath-dechu%2C+Rijo-Pius%2C+Eric-Marcoux%2C+mario-briggs&labels=agent-builder%2Corchestrate-lite-access-request&projects=&template=wxo-agent-builder-sdk-access-request.md&title=Orchestrate+Lite+Docker+Registry+Access+Request). Once approved the value to put on DOCKER_IAM_KEY will be emailed to you. 
6. Create a watsonx ai instance if you do not have one already and locate your space id. These can be found [here](https://dataplatform.cloud.ibm.com/developer-access?context=wx).
7. Create an env file with the following contents
```env
DOCKER_IAM_KEY=<will be emailed per step 5>
WATSONX_APIKEY=<your watsonx ai api key>
WATSONX_SPACE_ID=<your watsonx ai space id>
```

If you're working on WIPRO, Elevance, or are a PM/ developer on Watson Orchestrate, ping [@eric.marcoux](https://ibm.enterprise.slack.com/team/W3PNE8R3L) for watsonx.ai credentials if you do not have them already.

## Reporting issues
Please raise issues on [wo-tracker](https://github.ibm.com/WatsonOrchestrate/wo-tracker/issues/new?assignees=&labels=type-bug&projects=&template=1-wo-bug-report-template.md&title=BUG%3A+XXX)
and include the agent-builder and Defect labels.

## CLI Documentation

After installation, you will have access to the WXO CLI tool
This tool can be accessed using the `orchestrate` command

```bash
orchestrate --help

 Usage: orchestrate [OPTIONS] COMMAND [ARGS]...                                 
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ env                                                                          │
│ tools                                                                        │
│ agents                                                                       │
│ server                                                                       │
│ chat                                                                         │
╰──────────────────────────────────────────────────────────────────────────────╯

```
---

## Table of Contents
- [Getting started guide](./docs/0_getting_started.md)
- [Server start](./docs/1_server_start.md)
- [Agents](./docs/2_agents.md)
- [Tools](./docs/2_tools.md)
- [Connections](./docs/2_connections.md)


## SDK Developer Guide
A guide for how to install the sdk to develop sdk itself can be found [here](./docs/9_cli_development.md).
