# Run Flow Integration Tests
## Overview
This folder contains end-to-end tests for Flow. Each of the test cases here creates a flow, run the flow and verify the output result. The test cases inside this "integration_tests" need an actual running Orchestrate Server to execute. To run the integration tests, you can either set up the Orchestrate Server on your local testing environment, or use the `run_integration_tests.sh` to start a container which will spin up a Orchestrate Server within the container. 

## Pre-requisite
- You need to have a .env file with all the required credentials set up on the root folder of the wxo-clients repo, same as you are trying to set up the Orchestrate Server on your local machine. 
- You need to have a Docker engine running. Since when building the test image the `run_integration_tests.sh` will try to pull a `dind` image from `docker-na-public.artifactory.swg-devops.com`, you need access to this repo as well. 

## Running integration tests with container
You can use the `run_integration_tests.sh` to run the integration tests within a Docker container. It requires the test environment to have a running docker engine and a docker CLI (or Rancher Desktop).

Here is how to use the `run_integration_tests.sh` script:
    - `run_integration_tests.sh`: print message about how to use this script. 
    - `run_integration_tests.sh shell`: start the container with a running Orchestrate Server inside the container, and start a sh shell in the container to run the tests in an interactive way. 
    - `run_integration_tests.sh all`: start the container with a running Orchestrate Server inside the container, and run all the integration tests with `pytest`. 

### What is happenning
The `run_integration_tests.sh` will start a docker container with a Docker-inside-Docker image, also commonly known as `dind`. The image should be called `dind-with-python`. If this image does not exist, the script will build one. 

After starting the container, the `run_integration_tests.sh` will execute commands to install all the required dependencies through `pip` and start the Orchestrate Server inside the container. Then the container is ready to execute any tests either automatically or interactively. 

## Test Framework
All the tests, including all the integration tests within this folder, should be written and run with `pytest`.

## Adding New Test Case
By design, all the integration tests should go into the `integration_tests` folder. If you are adding flow tests, the test should be in the `flow_builder` folder. Then each flow test case should have its own folder. So let's say we have a flow test case called `hello_message_flow`, it should have a folder like `/wxo-clients/integration_tests/flow_builder/hello_message_flow`, and within `hello_message_flow` there should be all the required tools, agents, etc... that required to create the flow and run it. Then there should be at least one file starting with `test_`, like `test_hello_message_flow.py` that contains the test cases. 

All the files that contains the actual tests should have names start with `test_` otherwise `pytest` won't be able to recognize them. 