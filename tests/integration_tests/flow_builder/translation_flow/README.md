# Translation Flow Integration Tests

This directory contains integration tests for the flow translation export/import functionality.

## Overview

These tests validate the complete end-to-end workflow of:
1. Creating/importing a flow tool
2. Exporting translations to CSV format
3. Modifying translation content
4. Importing translations back to the system
5. Verifying translations are correctly applied

## Prerequisites

- A running Orchestrate Server (local Developer Edition or remote SaaS instance)
- Python environment with all dependencies installed
- Valid credentials configured in `.env` file at the repository root

## Running the Tests

### Option 1: Using Docker Container (Recommended)

From the `tests/integration_tests` directory:

```bash
# Run all integration tests including translation tests
./run_integration_tests.sh all

# Or start an interactive shell to run tests manually
./run_integration_tests.sh shell
pytest flow_builder/translation_flow/ -v -s
```

### Option 2: With Local Orchestrate Server

```bash
# Start the Orchestrate server
orchestrate server start

# Run the translation integration tests
pytest tests/integration_tests/flow_builder/translation_flow/ -v -s

# Run specific test class
pytest tests/integration_tests/flow_builder/translation_flow/test_translation_flow.py::TestTranslationExportIntegration -v

# Run specific test
pytest tests/integration_tests/flow_builder/translation_flow/test_translation_flow.py::TestTranslationExportIntegration::test_export_translations_from_file -v
```

## Test Structure

### Test Classes

1. **TestTranslationExportIntegration**
   - Tests translation export from files and imported tools
   - Validates CSV structure and content
   - Tests directory creation

2. **TestTranslationImportIntegration**
   - Tests translation import functionality
   - Validates roundtrip (export → modify → import → verify)
   - Tests import with tool ID and tool name

3. **TestTranslationCLIIntegration**
   - Tests CLI commands (`translationExport`, `translationImport`)
   - Validates command-line interface behavior
   - Tests translation import during tool import

4. **TestTranslationErrorHandling**
   - Tests error scenarios (nonexistent tools, invalid files)
   - Validates proper exception handling

### Fixtures

- `flow_json_file_path`: Returns the path to the flowJson.json test file
- `flow_model_from_file`: Loads the flow model from flowJson.json
- `imported_flow_tool`: Imports a flow tool and provides cleanup

### Test Files

- `tools/flowJson.json`: A properly structured flow model file used for testing translation export from files. Contains a flow with translation support enabled for French locale.
- `tools/translation_test_flow.py`: Python-based flow definition used by the `imported_flow_tool` fixture
- `tools/echo_tool.py`: Simple echo tool used within the test flow

## Expected Behavior

All tests should pass when:
- Orchestrate server is running and accessible
- Valid credentials are configured
- Network connectivity is available (for remote instances)

## Troubleshooting

### Server Not Running
```
Error: Connection refused
```
**Solution**: Start the Orchestrate server with `orchestrate server start`

### Authentication Errors
```
Error: 401 Unauthorized
```
**Solution**: Check your `.env` file has valid credentials

### Test Failures
- Check server logs for detailed error messages
- Verify the flow tool was created successfully
- Ensure CSV files are being generated correctly

## Adding New Tests

When adding new integration tests:
1. Follow the existing test structure and naming conventions
2. Use appropriate fixtures for setup and cleanup
3. Add docstrings explaining what the test validates
4. Ensure tests clean up resources after execution
5. Test both success and failure scenarios

## Related Documentation

- [Integration Tests Overview](../../README.md)
- [Flow Builder Documentation](../../../../_docs/flow_builder/)
- [Translation API Documentation](../../../../_docs/api/translations.md)