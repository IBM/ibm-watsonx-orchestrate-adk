import warnings
import re
warnings.filterwarnings(
    "ignore",
    message=re.escape("The 'validate_default' attribute with value True was provided to the `Field()` function, which has no effect in the context it was used."),
    category=UserWarning,
    module='pydantic'
)
import os
import sys
import time
import uuid
import json
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from pydantic.warnings import UnsupportedFieldAttributeWarning

OPENSEARCH_ENDPOINT = os.getenv('OPENSEARCH_ENDPOINT', 'https://localhost')
OPENSEARCH_PORT = os.getenv('OPENSEARCH_PORT', '9200')
OPENSEARCH_USERNAME = os.getenv('OPENSEARCH_USERNAME', 'admin')
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', '')

INDEX_NAME = os.getenv('INDEX_NAME', 'knowledge_vector_index')

CHUNK_SIZE = os.getenv('CHUNK_SIZE', 400)
CHUNK_OVERLAP = os.getenv('CHUNK_OVERLAP', 50)

MAX_SIZE_BYTES = 25 * 1024 * 1024

INGEST_WAIT_SECS = 5

headers = None
auth = HTTPBasicAuth(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)
TLS_VERIFY = False

warnings.filterwarnings('ignore', category=InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UnsupportedFieldAttributeWarning)

def ingest(document: dict):
    resp = requests.put(
        auth=auth,
        headers=headers,
        url=f'{OPENSEARCH_ENDPOINT}:{OPENSEARCH_PORT}/{INDEX_NAME}/_doc/{str(uuid.uuid4())}',
        json=json.loads(json.dumps(document)),
        verify=TLS_VERIFY,
    )
    resp.raise_for_status()
    
def main():

    if len(sys.argv) == 2:
        document_file_name = sys.argv[1]
    else:
        print("Usage: python ingest_document <document file name>")
        sys.exit(1)
        
    print()
    print("ingesting document")
    print()

    try:
        
        file_size = os.path.getsize(document_file_name)
        if file_size > MAX_SIZE_BYTES:
            print(f"The file size has exceed the supported 25 MB size limit")
            sys.exit(1)
    
        pdf_document = SimpleDirectoryReader(input_files=[f"{document_file_name}"]).load_data() 
        splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        
        paragraphs = []
        for document in pdf_document:
            paragraphs.extend(splitter.split_text(document.text))
        
        for index in range(len(paragraphs)):
            print('.', end='')
            document = {
                "title": document_file_name,
                "passage_text": paragraphs[index],
            }
            try:
                ingest(document)
            except HTTPError as http_err:
                if http_err.response.status_code == 429:
                    print()
                    print(f"Received 429 error when ingesting document: {index}, will wait for {INGEST_WAIT_SECS} seconds, then retry")
                    time.sleep(INGEST_WAIT_SECS)
                    ingest(document)
                    print(f"The ingestion retry of document {index} succeeded.")
                else:
                    raise    
            
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Status Code: {http_err.response.status_code}")
        print(f"Reason: {http_err.response.reason}")
        print(f"Response Content: {http_err.response.text}")
        sys.exit(1)
    except Exception as err:
        print(f"Other error occurred: {err}")
        sys.exit(1)

    print()
    print("The document was ingested successfully")
    print()


if __name__ == "__main__":
    main()
