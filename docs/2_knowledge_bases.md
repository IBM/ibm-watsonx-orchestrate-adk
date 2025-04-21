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

  2. External Milvus/ElasticSearch will be used if the knowledge base file contains `conversational_search_tool.index_config`

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
