# Define apps

# Create connections

# Set credentials

# Import tools that have auth

# Import tools with no auth

# Import flows
orchestrate tools import -k flow -f ./tools/context_variables.json
orchestrate tools import -k flow -f ./tools/onboarding_checklist.json
# Import knowledge base

# Import agents
orchestrate agents import -f ./agents/HR_agent.yaml
