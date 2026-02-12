import os
import sys
import json
import warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

OPENSEARCH_ENDPOINT = os.getenv('OPENSEARCH_ENDPOINT', 'https://localhost')
OPENSEARCH_PORT = os.getenv('OPENSEARCH_PORT', '9200')
OPENSEARCH_USERNAME = os.getenv('OPENSEARCH_USERNAME', 'admin')
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', '')

INDEX_NAME = os.getenv('INDEX_NAME', 'knowledge_vector_index')
INGEST_PIPELINE_NAME = os.getenv('INGEST_PIPELINE_NAME', 'ingest_pipeline')
SEARCH_PIPELINE_NAME = os.getenv('SEARCH_PIPELINE_NAME', 'search_pipeline')

headers = None
auth = HTTPBasicAuth(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)
TLS_VERIFY = False

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def main():

    print("creating vector index")

    try:
        payload = {
          "settings": {
            "index.knn": True,
            "default_pipeline": INGEST_PIPELINE_NAME
          },
          "mappings": {
            "properties": {
              "id": {
                "type": "text"
              },
              "passage_embedding": {
                "type": "knn_vector",
                "dimension": 768,
                "method": {
                  "engine": "lucene",
                  "space_type": "l2",
                  "name": "hnsw",
                  "parameters": {}
                }
              },
              "passage_text": {
                "type": "text"
              }
            }
          }
        }
        
        resp = requests.put(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/{INDEX_NAME}',
            json=json.loads(json.dumps(payload)),
            verify=TLS_VERIFY,
        )
        resp.raise_for_status()
        
        payload = {
          "index.search.default_pipeline" : SEARCH_PIPELINE_NAME
        }
        
        resp = requests.put(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/{INDEX_NAME}/_settings',
            json=json.loads(json.dumps(payload)),
            verify=TLS_VERIFY,
        )
        resp.raise_for_status()
        
    
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Status Code: {http_err.response.status_code}")
        print(f"Reason: {http_err.response.reason}")
        print(f"Response Content: {http_err.response.text}")
        sys.exit(1)
    except Exception as err:
        print(f"Other error occurred: {err}")
        sys.exit(1)
    
    print("The vector index was created successfully")


if __name__ == "__main__":
    main()
