import os

# Knowledge connectors (content_source / external-source ingestion) are disabled by default.
# Set KNOWLEDGE_CONNECTORS_ENABLED=true to enable the feature.
KNOWLEDGE_CONNECTORS_ENABLED = os.environ.get("KNOWLEDGE_CONNECTORS_ENABLED", "false").lower() == "true"
