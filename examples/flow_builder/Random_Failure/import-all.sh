# Define apps

# Create connections

# Set credentials

# Import tools 
orchestrate tools import -k python -f Tools/randomNumber.py
orchestrate tools import -k python -f Tools/backupRandomNumber.py



# Import flows
orchestrate tools import -k flow -f ./Tools/random_failure_flow.json

# Import knowledge base

# Import agents
orchestrate agents import -f ./Agents/testAgent.yaml
