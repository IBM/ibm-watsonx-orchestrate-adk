#!/usr/bin/env bash
#
# Set up the Box knowledge base example.
#
# Creates the Box connection, imports the knowledge base, and imports the agent.
#
# Prerequisites:
#   - jq (JSON processor): brew install jq (macOS) or apt-get install jq (Linux)
#   - orchestrate CLI configured and authenticated
#
# Usage:
#   ./import_all.sh [config_file]
#
# Example:
#   ./import_all.sh config-box.json

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CONFIG_FILE="${1:-${SCRIPT_DIR}/config-box.json}"

# ---------------------------------------------------------------------------
# 1. Box connection
# ---------------------------------------------------------------------------
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Box Connection Setup${NC}"
echo -e "${BLUE}========================================${NC}\n"

if ! command -v jq &> /dev/null; then
    echo -e "${RED}✗ jq is not installed${NC}"
    echo -e "${YELLOW}Install with: brew install jq (macOS) or apt-get install jq (Linux)${NC}"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗ Credentials file not found: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Copy config-box-template.json to config-box.json and fill in your Box credentials${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Credentials file: $CONFIG_FILE\n"

CLIENT_ID=$(jq -r '.connection_properties.client_id' "$CONFIG_FILE")
CLIENT_SECRET=$(jq -r '.connection_properties.client_secret' "$CONFIG_FILE")
ENTERPRISE_ID=$(jq -r '.connection_properties.enterprise_id' "$CONFIG_FILE")
PUBLIC_KEY=$(jq -r '.connection_properties.public_key' "$CONFIG_FILE")
PRIVATE_KEY=$(jq -r '.connection_properties.private_key' "$CONFIG_FILE")
PRIVATE_KEY_PASSWORD=$(jq -r '.connection_properties.private_key_password' "$CONFIG_FILE")

echo -e "${YELLOW}Adding connection...${NC}"
orchestrate connections add -a box || echo -e "${YELLOW}⚠ 'connections add' failed (connection may already exist) — continuing${NC}"

echo -e "\n${YELLOW}Configuring connection (draft)...${NC}"
orchestrate connections configure -a box --kind key_value --type team --env draft || echo -e "${YELLOW}⚠ 'connections configure' failed (connection may already be configured) — continuing${NC}"

echo -e "\n${YELLOW}Setting credentials (draft)...${NC}"
orchestrate connections set-credentials -a box \
  --entries "client_id=${CLIENT_ID}" \
  --entries "client_secret=${CLIENT_SECRET}" \
  --entries "enterprise_id=${ENTERPRISE_ID}" \
  --entries "public_key=${PUBLIC_KEY}" \
  --entries "private_key=${PRIVATE_KEY}" \
  --entries "private_key_password=${PRIVATE_KEY_PASSWORD}" \
  --env draft || echo -e "${YELLOW}⚠ 'connections set-credentials' failed — continuing${NC}"

echo -e "\n${GREEN}✓ Box connection created${NC}\n"

# ---------------------------------------------------------------------------
# 2. Knowledge base + agent
# ---------------------------------------------------------------------------
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Importing Knowledge Base & Agent${NC}"
echo -e "${BLUE}========================================${NC}\n"

orchestrate knowledge-bases import -f "${SCRIPT_DIR}/knowledge_base/box_knowledge_base.yaml" -a box
orchestrate agents import -f "${SCRIPT_DIR}/agents/hr_benefits_agent.yaml"

echo -e "\n${GREEN}✓ Done!${NC}"
