# Define apps

# Create connections

# Set credentials

# Import tools that have auth

# Import tools with no auth
orchestrate tools import -k python -f Tools/get_countries_by_continent.py

# Import flows
orchestrate tools import -k flow -f ./Tools/IT_access_request_form.json

# Import knowledge base

# Import agents
orchestrate agents import -f ./Agents/IT_agent.yaml