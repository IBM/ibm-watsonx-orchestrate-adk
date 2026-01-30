import os
import sys
import json
import time
import warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

OPENSEARCH_ENDPOINT = os.getenv('OPENSEARCH_ENDPOINT', 'https://localhost')
OPENSEARCH_PORT = os.getenv('OPENSEARCH_PORT', '9200')
OPENSEARCH_USERNAME = os.getenv('OPENSEARCH_USERNAME', 'admin')
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', '')

MODEL_GROUP_NAME = os.getenv('MODEL_GROUP_NAME', 'local_model_group')

MODEL_NAME = os.getenv('MODEL_NAME', 'huggingface/sentence-transformers/msmarco-distilbert-base-tas-b')
MODEL_VERSION = os.getenv('MODEL_VERSION', '1.0.3')
MODEL_FORMAT = os.getenv('MODEL_FORMAT', 'TORCH_SCRIPT')

REGISTER_MODEL_ATTEMPTS = os.getenv('REGISTER_MODEL_ATTEMPTS', 5)
REGISTER_MODEL_WAIT_SECS = os.getenv('REGISTER_MODEL_WAIT_SECS', 8)

INGEST_PIPELINE_NAME = os.getenv('INGEST_PIPELINE_NAME', 'ingest_pipeline')
SEARCH_PIPELINE_NAME = os.getenv('SEARCH_PIPELINE_NAME', 'search_pipeline')

headers = None
auth = HTTPBasicAuth(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)
TLS_VERIFY = False

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def main():

    try:
        # 1. enabling machine learning
        print()
        print("1. enabling machine learning in the opensearch cluster")
        print()
        
        payload = {
          "persistent": {
            "plugins.ml_commons.only_run_on_ml_node": "false",
            "plugins.ml_commons.model_access_control_enabled": "true",
            "plugins.ml_commons.native_memory_threshold": "99"
          }
        }
    
        resp = requests.put(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_cluster/settings',
            json=json.loads(json.dumps(payload)),
            verify=TLS_VERIFY,
        )
        resp.raise_for_status()
        
    
        # 2. registering model group
        print()
        print("2. registering model group")
        print()

        payload ={
          "query": {
            "match": {
              "name": MODEL_GROUP_NAME
            }
          }
        }
        
        resp = requests.get(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_plugins/_ml/model_groups/_search',
            verify=TLS_VERIFY,
            json=json.loads(json.dumps(payload)),
        )
        resp.raise_for_status()
        
        if len(resp.json()["hits"]["hits"]) > 0:
            model_group_id = resp.json()["hits"]["hits"][0]["_id"]
            print(f"found existing model group id: {model_group_id}")
        else:
            payload ={
              "name": MODEL_GROUP_NAME,
              "description": "A model group for local models"
            }

            resp = requests.post(
                auth=auth,
                headers=headers,
                url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_plugins/_ml/model_groups/_register',
                json=json.loads(json.dumps(payload)),
                verify=TLS_VERIFY,
            )
            resp.raise_for_status()
            
            model_group_id = resp.json()["model_group_id"]
            print(f"registered model group id: {model_group_id}")
    
        # 3. registering model 
        print()
        print("3. registering model")
        print()
        
        payload ={
          "name": MODEL_NAME,
          "version": MODEL_VERSION,
          "model_group_id": model_group_id,
          "model_format": MODEL_FORMAT,
        }
    
        resp = requests.post(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_plugins/_ml/models/_register',
            json=json.loads(json.dumps(payload)),
            verify=TLS_VERIFY,
        )
        resp.raise_for_status()
    
        task_id = resp.json()["task_id"]

        print(f"register model task id: {task_id}")
        
        
        # 4. obtaining model id
        print()
        print("4. obtaining model id")
        print()

        model_id = None
        for i in range(REGISTER_MODEL_ATTEMPTS):
            time.sleep(REGISTER_MODEL_WAIT_SECS)
            resp = requests.get(
                auth=auth,
                headers=headers,
                url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_plugins/_ml/tasks/{task_id}',
                verify=TLS_VERIFY,
            )
            resp.raise_for_status()
            state = resp.json()["state"]
            if state == 'COMPLETED':
                model_id = resp.json()["model_id"]
                break
        
        if model_id is None:
            raise ValueError("Failed to obtain model id.")    
    
        print(f"registered model id: {model_id}")
    
        # 5. deploying model
        print()
        print("5. deploying model")
        print()
        
        resp = requests.post(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_plugins/_ml/models/{model_id}/_deploy',
            verify=TLS_VERIFY,
        )
        resp.raise_for_status()
    
    
        # 6. creating ingest pipeline
        print()
        print("6. creating ingest pipeline")
        print()
        
        payload = {
          "description": "A text embedding pipeline",
          "processors": [
            {
              "text_embedding": {
                "model_id": model_id,
                "field_map": {
                  "passage_text": "passage_embedding"
                }
              }
            }
          ]
        }
        
        resp = requests.put(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_ingest/pipeline/{INGEST_PIPELINE_NAME}',
            json=json.loads(json.dumps(payload)),
            verify=TLS_VERIFY,
        )
        resp.raise_for_status()
    
    
        # 7. creating search pipeline
        print()
        print("7. creating search pipeline")
        print()
    
        payload = {
          "request_processors": [
            {
              "neural_query_enricher" : {
                "default_model_id": model_id,
              }
            }
          ]
        }
        
        resp = requests.put(
            auth=auth,
            headers=headers,
            url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/_search/pipeline/{SEARCH_PIPELINE_NAME}',
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
    
    print("The model was registered and the pipelines were created successfully")


if __name__ == "__main__":
    main()
