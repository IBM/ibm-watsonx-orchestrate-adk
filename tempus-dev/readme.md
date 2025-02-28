1. Install the correct python version as per the requirement of the wxo-clients Readme
   - A handy tool to manage different Python versions - https://github.com/pyenv/pyenv
2. Git clone the the `wxo-clients` repo to your environment and cd to the repo directory
3. Run `pip install venv && python -m venv .venv` to create a virtual environment so that the pip packages will be downloaded to this directory
4. Run `source .venv/bin/activate` to activate the virtual environment
5. Run `docker login docker-na-public.artifactory.swg-devops.com` with your w3ID as the username and Artifactory token as the password
6. Follow the wxo-clients Readme to complete the rest of the setup
   - !! Note: Instead of running `pip install git+ssh://git@github.ibm.com/WatsonOrchestrate/wxo-clients.git` do `pip install -e .` under the `wxo-clients` project root instead. This also means that you don't have to upload your local SSH public key to the Github
