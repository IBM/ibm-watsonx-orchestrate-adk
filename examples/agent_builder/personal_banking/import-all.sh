#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Load environment variables if .env exists
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
fi

echo "📦 Setting up AstraDB connection..."

# Import single connection for personal banking app
orchestrate connections add --app-id personal_banking_app
orchestrate connections configure -a personal_banking_app --env draft --kind key_value --type team

# Set credentials (requires ASTRA_TOKEN and ASTRA_URL environment variables)
if [ -z "$ASTRA_TOKEN" ] || [ -z "$ASTRA_URL" ]; then
    echo "⚠️  ASTRA_TOKEN and/or ASTRA_URL not set. Please set them manually:"
    echo "   orchestrate connections set-credentials -a personal_banking_app --env draft -e ASTRA_TOKEN=<YOUR_TOKEN> -e ASTRA_URL=<YOUR_ENDPOINT> -e ASTRA_NAMESPACE=<YOUR_NAMESPACE>"
else
    # Set namespace (default to 'default_keyspace' if not provided)
    NAMESPACE=${ASTRA_NAMESPACE:-default_keyspace}
    orchestrate connections set-credentials -a personal_banking_app --env draft -e ASTRA_TOKEN=$ASTRA_TOKEN -e ASTRA_URL=$ASTRA_URL -e ASTRA_NAMESPACE=$NAMESPACE
    echo "✅ Personal Banking App connection configured"
    echo "   - Token: ${ASTRA_TOKEN:0:10}..."
    echo "   - Endpoint: $ASTRA_URL"
    echo "   - Namespace: $NAMESPACE"
fi

echo ""
echo "🔧 Importing Python tools..."
# Import Python tools with requirements
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/transfer_money.py -r ${SCRIPT_DIR}/tools/requirements.txt --app-id personal_banking_app
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/list_accounts.py -r ${SCRIPT_DIR}/tools/requirements.txt --app-id personal_banking_app
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/get_contact.py -r ${SCRIPT_DIR}/tools/requirements.txt --app-id personal_banking_app
orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/change_contact.py -r ${SCRIPT_DIR}/tools/requirements.txt --app-id personal_banking_app

echo ""
echo "🤖 Importing agent..."
# Import agent
orchestrate agents import -f ${SCRIPT_DIR}/agents/personal_banking_agent.yaml

echo ""
echo "✅ Import complete!"
echo ""
echo "📝 Next steps:"
echo "1. If you haven't set ASTRA_TOKEN/ASTRA_URL, configure the connection:"
echo "   orchestrate connections set-credentials -a personal_banking_app --env draft -e ASTRA_TOKEN=<YOUR_TOKEN> -e ASTRA_URL=<YOUR_ENDPOINT> -e ASTRA_NAMESPACE=<YOUR_NAMESPACE>"
echo ""
echo "2. Create the AstraDB table using the setup script:"
echo "   ./setup_astra_table.sh"
echo ""
echo "3. Test the re-entrant flow tool:"
echo "   orchestrate chat -a personal_banking_agent"
echo ""
echo "Try these commands:"
echo "  - Transfer \$100 from CHK-001 to SAV-002"
echo "  - What's the status?"
echo "  - Cancel the transfer"

# Made with Bob
