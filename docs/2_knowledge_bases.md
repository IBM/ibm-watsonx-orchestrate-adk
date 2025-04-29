# Knowledge Bases

## Import Knowledge Bases
#### `orchestrate knowledge-bases import`
This command allows a user to import knowledge bases into the WXO platform
There are 2 kinds of knowledge base imports, built-in milvus and external milvus/elastic search, determined by the format of the knowledge base file, which is required to be passed through the `--file` of `-f` flag

  1. Built-In Milvus will be used if the knowledge base file contains `documents`

   `orchestrate knowledge-bases import -f <knowledge-base-file-path>`
   ```yaml
      spec_version: v1
      kind: knowledge_base 
      name: "myName"
      description: "The description"
      documents:
       - "/file-path-1.pdf",
       - "/file-path-2.pdf"
        
   ```

  2. External Milvus/Elasticsearch will be used if the knowledge base file contains `conversational_search_tool.index_config`

   ##### External Milvus Example

   `orchestrate knowledge-bases import -f <knowledge-base-file-path>`
   ```yaml
      spec_version: v1
      kind: knowledge_base 
      name: "myName"
      description: "The description"
      prioritize_built_in_index: false
      conversational_search_tool:
         index_config:
            - milvus:
               grpc_host: "my.grpc-host.com",
               grpc_port: "1234",
               database: "default",
               collection: "collection-name",
               index: "index-name",
               embedding_model_id: "ibm/slate-125m-english-rtrvr",
               filter: "<filter for search>",
               field_mapping:
                  title: "title",
                  body: "text"
   ```

   ##### External Elasticsearch Example
   `orchestrate knowledge-bases import -f <knowledge-base-file-path>`
   ```yaml
      spec_version: v1
      kind: knowledge_base 
      name: "myName"
      description: "The description"
      prioritize_built_in_index: false
      conversational_search_tool:
         index_config:
            - elastic_search:
               url: https://my.elasticsearch-instance.com
               index: my-index-name
               port: "1234"
               # Custom query_body can be provided to be sent to Elasticsearch. 
               # If provided, it must include the $QUERY token, which will be replaced by the user's query at runtime
               # Below is an example query_body using ELSER
               query_body: {"size":10,"query":{"text_expansion":{"ml.tokens":{"model_id":".elser_model_2_linux-x86_64","model_text": "$QUERY"}}}}
               field_mapping:
                  title: "title"
                  body: "text"
   ```


## Patch Knowledge Bases
#### `orchestrate knowledge-bases patch`
This command allows a user to update one of their knowledge bases
There are 2 kinds of knowledge base imports, built-in milvus and external milvus/elastic search, determined by the format of the knowledge base file, which is required to be passed through the `--file` of `-f` flag

  1. Documents can be added to a built-in knowledge base by including `documents` in the patch file. This list should only contian the new documents, and not any previously added documents

   `orchestrate knowledge-bases patch -n myName -f <knowledge-base-patch-file-path>`
   ```yaml
      description: "The updated description"
      documents:
       - "/file-path-3.pdf",
       - "/file-path-4.pdf"
        
   ```

  2. External Milvus/ElasticSearch configuration can be updated by including `conversational_search_tool.index_config`

   ``orchestrate knowledge-bases patch -n myName -f <knowledge-base-patch-file-path>`
   ```yaml
      description: "The updated description"
      conversational_search_tool:
         index_config:
            - milvus:
               grpc_host: "my.grpc-host.com",
               grpc_port: "1234",
               database: "default",
               collection: "collection-name",
               index: "index-name",
               embedding_model_id: "ibm/slate-125m-english-rtrvr",
               filter: "<filter for search>",
               field_mapping:
                  title: "title",
                  body: "text"
   ```

## Knowledge Base Status
To get the status of an existing knowledge base, simply run the following. For built-in Knowledge Bases, this will include a `Ready` property, which will denote whether your index has successfully been created, and the knowledge base is ready to use: 
```bash
orchestrate knowledge-bases status --name my-base-name
``` 

## Remove Knowledge Base
To remove an existing knowledge base, simply run the following: 
```bash
orchestrate knowledge-bases remove --name my-base-name
```

## List Knowledge Bases
To list all knowledge base, simply run the following: 
```bash
orchestrate knowledge-bases list
```
