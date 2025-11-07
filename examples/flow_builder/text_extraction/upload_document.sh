#!/bin/bash

##
## IBM Confidential
## OCO Source Materials
## 5737-I23
## Copyright IBM Corp. 2018 - 2025
## The source code for this program is not published or otherwise divested of its trade secrets, irrespective of what has been deposited with the U.S Copyright Office.
##
upload_document_to_s3() {
    local resp=$(curl -s -X POST ${URL}/orchestrate/upload-to-s3/\
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H 'accept: application/json' \
    -H 'Content-Type: multipart/form-data' \
    -F "files=@$FILE_PATH;type=application/pdf" \
    -F "id=testing")

    decoded_json=$(echo "$resp" | jq -r '.')
    ref=$(echo "$decoded_json" | jq '.[0].url' | jq -r .)
    echo "$ref"
}

upload_document_to_wxo_document_store() {
    local coll_id

    if [ -f "$COLLECTION_ID_FILE" ]; then 
        coll_id=`cat $COLLECTION_ID_FILE`
    else      
        curl -X POST $URL/document-collections \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -d '{
                "title": "doc-processing",
                "description": "Document Processing",
                "tags": ["doc-processing"],
                "name": "doc-processing"
            }'

        local response=$(curl -X GET $URL/document-collections \
                    -H "Content-Type: application/json" \
                    -H "Authorization: Bearer $JWT_TOKEN" \
                    -H "x-ibm-thread-id: $THREAD_ID")

        decoded_json=$(echo "$response" | jq -r '.')
        coll_id=$(echo "$decoded_json" | jq '.[0].id' | jq -r .)
        echo $coll_id > $COLLECTION_ID_FILE
    fi

    check_if_document_is_already_uploaded

    # post document
    payload=$(jq -n \
    --arg title "$FILE_PATH" \
    --arg collection_id "$coll_id" \
    '{
        title: $title,
        description: $title,
        tags: [$title],
        name: $title,
        collection_id: $collection_id,
        meta: {},
        source_uri: "string",
        source_date: "2025-06-24",
        source_name: $title,
        source_title: $title
    }')

    curl -X POST "$URL/documents" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d "$payload"

    local resp=$(curl -X GET $URL/documents \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $JWT_TOKEN" \
                -H "x-ibm-thread-id: $THREAD_ID")

    decoded_json=$(echo "$resp" | jq -r '.')
    local doc_id=$(echo "$decoded_json" | jq -cr --arg path "$FILE_PATH" '.[] | select(.source_name == $path) | .id')

    # upload document
    curl -X POST "$URL/documents/$doc_id/upload?extraction_strategy=auto" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@$FILE_PATH"

    jq --arg key "$FILE_PATH" --arg value "$doc_id" '. + {($key): $value}' "$JSON_FILE_PATH" > tmp.json && mv tmp.json "$JSON_FILE_PATH"
    echo "Document id of $FILE_PATH: $doc_id"
}

check_if_document_is_already_uploaded() {
    if jq -e ". | has(\"$FILE_PATH\")" "$JSON_FILE_PATH" > /dev/null; then
        echo "Document id of $FILE_PATH: $(jq -r ".\"$FILE_PATH\"" "$JSON_FILE_PATH")"
        exit 0
    fi
}

print_usage() {
    echo ""
    echo "Usage: upload_document.sh -f <FILE_ABSOLUTE_PATH>"
    echo "This script will take a file absolute path, upload it to wxo document store and get the document id for the file."
    echo "The documment id will be stored as ~/.documents/files.json and the file absolute path will be associated with a document id."
    echo "IF YOU RUN orchestrate server reset, REMOVE ~/.documents"
    echo ""
}


FILE_PATH=
case "$1" in
-h | --help)
    print_usage
    exit 0
    ;;
-f)
    FILE_PATH="$2"
    ;;
esac

if [[ ! -f "${FILE_PATH}" ]]; then
    echo "File does not exists."
    exit 1
fi

ORCHESTRATE_CRED_YAML=~/.cache/orchestrate/credentials.yaml
THREAD_ID=a606063c-d8ed-4f36-a43d-aa7dee11f5a0
URL=http://localhost:4321/api/v1
JSON_FILE_PATH=~/.documents/files.json
COLLECTION_ID_FILE=~/.documents/collection_id
JWT_TOKEN=`awk '/local:/ {f=1} f && /wxo_mcsp_token:/ {print $2; exit}' $ORCHESTRATE_CRED_YAML`


mkdir -p ~/.documents


if [ ! -f "${JSON_FILE_PATH}" ]; then
    touch $JSON_FILE_PATH
    echo '{}' > "$JSON_FILE_PATH"
fi

#upload_document_to_wxo_document_store
upload_document_to_s3