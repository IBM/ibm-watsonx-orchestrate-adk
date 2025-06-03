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

