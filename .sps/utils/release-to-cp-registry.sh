API_KEY=$1
ENV_FILE=$2
DRY_RUN=${3:-false}


skopeo login us.icr.io -u iamapikey -p "${API_KEY}"
skopeo login cp.icr.io -u iamapikey -p "${API_KEY}"
skopeo login icr.io -u iamapikey -p "${API_KEY}"

source $ENV_FILE

images=$(cat <<EOF
wxo-server-db:${DBTAG}
wxo-connections:${CM_TAG}
wxo-connections-ui:${CONNECTIONS_UI_TAG}
ai-gateway:${AI_GATEWAY_TAG}
wxo-agent-gateway:${AGENT_GATEWAY_TAG}
wxo-chat:${UITAG}
wxo-builder:${BUILDER_TAG}
wxo-socket-handler:${SOCKET_HANDLER_TAG}
wxo-server-server:${SERVER_TAG}
wxo-server-conversation_controller:${WORKER_TAG}
tools-runtime-manager:${TRM_TAG}
tools-runtime:${TR_TAG}
jaeger-proxy:${JAEGER_PROXY_TAG}
agentops-backend:${AGENT_ANALYTICS_TAG}
wxo-tempus-runtime:${FLOW_RUNTIME_TAG}
wxo-prompt-optimizer:${CPE_TAG}
document-processing/wo_doc_processing_service:${DOCPROC_DPS_TAG}
document-processing/wdu-runtime:${WDU_TAG}
document-processing/wdu-models:${WDU_TAG}
document-processing/wo-doc-processing-infra-standalone:${DOCPROC_DPI_TAG}
document-processing/wo-doc-processing-infra-pg-init:${DOCPROC_DPI_TAG}
document-processing/wo_doc_processing_rag:${DOCPROC_LLMSERVICE_TAG}
document-processing/wo_doc_processing_cache:${DOCPROC_CACHE_TAG}
document-processing/wo_doc_processing_cache_rds_init:${DOCPROC_CACHE_TAG}
wxo-agent-architect-server:${AGENT_ARCHITECT_TAG}
wxo-agent-runtime:${AR_TAG}
mcp-gateway:${MCP_GATEWAY_TAG}
EOF)

for image in  $images; do
    if skopeo inspect docker://cp.icr.io/cp/wxo-lite/${image} > /dev/null 2>&1; then
      echo "cp.icr.io/cp/wxo-lite/${image} exists in wxo-lite repo, skipping."
    else
      echo "Copying us.icr.io/watson-orchestrate-private/${image} to icr.io/cp/wxo-lite/${image} repo."
      if [ "$DRY_RUN" == "false" ]; then
        skopeo copy --multi-arch all docker://us.icr.io/watson-orchestrate-private/${image} docker://icr.io/cp/wxo-lite/${image} --preserve-digests
      else
        echo "skopeo copy --multi-arch all docker://us.icr.io/watson-orchestrate-private/${image} docker://icr.io/cp/wxo-lite/${image} --preserve-digests"
      fi
    fi
done

