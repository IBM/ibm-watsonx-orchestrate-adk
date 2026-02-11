### How to run evaluation with file upload

This example demonstrates how to evaluate an agent that uses **file upload functionality**. File uploads allow the agent to receive and process files (such as employee ID cards for verification) as part of the conversation workflow.

#### Key Differences from Standard Evaluation

1. **Agent Definition**: The agent includes tools that accept file content as parameters (e.g., `upload_employee_id_card` with `file_content: bytes` parameter).

2. **Test Data**: Each test case includes a `file_upload` field that specifies the file to be uploaded during the test scenario, including the file path, file ID, and content type.

#### Setup

1. Run `import-all.sh` to import the tools and agent:
   ```bash
   ./examples/evaluations/evaluate_with_file_upload/import-all.sh
   ```

2. Run the evaluation:
   ```bash
   orchestrate evaluations evaluate -p ./examples/evaluations/evaluate_with_file_upload/ -o ./debug -e .env_file
   ```

#### File Upload in Test Data

The test data file [data_file_upload.json](data_file_upload.json) includes a `file_upload` field:

```json
{
  ...
  "file_upload": {
    "file_path": "examples/evaluations/evaluate_with_file_upload/sample-id.jpg",
    "file_id": "001",
    "content_type": "image/jpeg"
  }
}
```

This simulates a scenario where the user uploads their employee ID card for verification before the agent processes their HR request. The agent uses the uploaded file to authenticate the user's identity automatically.


#### Test Scenarios

- **data_file_upload.json**: A user querying their time-off schedule and uploading their employee ID card for verification
