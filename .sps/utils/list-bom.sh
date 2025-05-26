ENV_FILE=$1

source $ENV_FILE

images=$(cat <<EOF
wxo-server-db:${DBTAG}
wxo-connections:${CM_TAG}
wxo-chat:${UITAG}
wxo-builder:${BUILDER_TAG}
wxo-server-server:${SERVER_TAG}
wxo-server-conversation_controller:${WORKER_TAG}
tools-runtime-manager:${TRM_TAG}
tools-runtime:${TR_TAG}
ai-gateway:${AI_GATEWAY_TAG}
wxo-tempus-runtime:${FLOW_RUNTIME_TAG}
EOF)

for image in  $images; do
	echo "us.icr.io/watson-orchestrate-private/${image}"
done


