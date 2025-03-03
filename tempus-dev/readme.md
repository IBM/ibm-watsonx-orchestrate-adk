1. Install the correct python version as per the requirement of the wxo-clients Readme
   - A handy tool to manage different Python versions - https://github.com/pyenv/pyenv
2. Git clone the the `wxo-clients` repo to your environment and cd to the repo directory
3. Run `pip install venv && python -m venv .venv` to create a virtual environment so that the pip packages will be downloaded to this directory
4. Run `source .venv/bin/activate` to activate the virtual environment
5. Run `docker login docker-na-public.artifactory.swg-devops.com` with your w3ID as the username and Artifactory token as the password
6. Optional - To validate MaPE (also CFE) can retrieve content from the file system
   - Download the CMC widgets for MaPE from https://ibm.box.com/s/f0f0vwjooelbsg6vnj1cwghwbw9uoisc and unzip all the contents from the "widgets" directory to "src/ibm_watsonx_orchestrate/docker/tempus/cfe/cmc/CommonModelContainer/widgets"
   - Download the sample project zip from https://ibm.box.com/s/45ev4skfcxdzldliclpitenpzrm6j8gj and put the unzipped folders to "src/ibm_watsonx_orchestrate/docker/tempus/cfe/uab"
   - Follow [the section below](#optional---to-validate-mape-also-cfe-can-retrieve-content-from-the-file-system) to validate after the containers are up and running
7. Follow the wxo-clients Readme to complete the rest of the setup
   - !! Note: Instead of running `pip install git+ssh://git@github.ibm.com/WatsonOrchestrate/wxo-clients.git` do `pip install -e .` under the `wxo-clients` project root instead. This also means that you don't have to upload your local SSH public key to the Github

---

### Optional - To validate MaPE (also CFE) can retrieve content from the file system

To review MaPE content served through the Browser:

1. Go to https://localhost:3001
2. Open DevTool -> Application tab -> Cookie -> https://localhost:3001
3. Add a new cookie
   - Name: __Secure-idt
   - Value: JWT Retrieved from your environment "~/.cache/orchestrate/credentials.yaml"
   - Domain: localhost
   - Path: /
   - Expires: Session
   - HttpOnly: √
   - Secure: √
4. Try through https://localhost:3001/asb/cfe/v1/[org]~[projectId]~[modelId]/[file]
   - e.g. https://localhost:3001/asb/cfe/v1/uab~jltest011601~jltest011601w1/app_1.63215c6b-0f8b-4d9a-b613-15d32d677231 from the sample zip
