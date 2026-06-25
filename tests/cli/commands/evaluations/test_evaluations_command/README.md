# Evaluation Commands Test Suite

This directory contains organized tests for all evaluation commands and subcommands.

## Structure

```
test_evaluations_command/
├── __init__.py                          # Package marker
├── conftest.py                          # Shared fixtures for all tests
├── test_evaluate/                       # Main evaluate command tests
│   ├── __init__.py
│   └── test_evaluate.py
├── test_analyze/                        # Tests for analyze command
│   ├── __init__.py
│   └── test_analyze.py
├── test_generate/                       # Tests for generate command
│   ├── __init__.py
│   └── test_generate.py
├── test_quick_eval/                     # Tests for quick-eval command
│   ├── __init__.py
│   └── test_quick_eval.py
├── test_record/                         # Tests for record command
│   ├── __init__.py
│   └── test_record.py
├── test_red_teaming/                    # Tests for red-teaming commands
│   ├── __init__.py
│   └── test_red_teaming.py
├── test_validate_external/              # Tests for validate-external command
│   ├── __init__.py
│   └── test_validate_external.py
├── test_validate_native/                # Tests for validate-native command
│   ├── __init__.py
│   └── test_validate_native.py
└── test_environment_manager/            # Tests for environment manager
    ├── __init__.py
    └── test_environment_manager.py
```

## Shared Fixtures (conftest.py)

The following fixtures are available to all tests:

- `user_env_file` - Temporary .env file with test credentials (auto-used, module scope)
- `valid_config` - Standard configuration dictionary
- `config_file` - Temporary JSON config file
- `external_agent_config` - Temporary external agent config file

## Running Tests

### Run all evaluation tests:
```bash
pytest tests/cli/commands/evaluations/test_evaluations_command/
```

### Run specific subcommand tests:
```bash
# Test only the main evaluate command
pytest tests/cli/commands/evaluations/test_evaluations_command/test_evaluate/

# Test only quick-eval
pytest tests/cli/commands/evaluations/test_evaluations_command/test_quick_eval/

# Test only validate-external
pytest tests/cli/commands/evaluations/test_evaluations_command/test_validate_external/

# Test only red-teaming
pytest tests/cli/commands/evaluations/test_evaluations_command/test_red_teaming/
```

### Run specific test classes or methods:
```bash
# Run only USE_LEGACY_EVAL flag tests
pytest tests/cli/commands/evaluations/test_evaluations_command/test_evaluate/test_evaluate.py::TestLegacyEvalFlag

# Run a specific test
pytest tests/cli/commands/evaluations/test_evaluations_command/test_evaluate/test_evaluate.py::TestLegacyEvalFlag::test_evaluate_with_legacy_eval_false
```

## Test Coverage

### Main Evaluate Command (`test_evaluate/test_evaluate.py`)
- **TestEvaluate**: Basic evaluate command functionality
- **TestLegacyEvalFlag**: Tests for USE_LEGACY_EVAL flag behavior (TRUE/FALSE)
- **TestEvaluateCommandOptions**: Tests for all command-line options:
  - `--config/-c`
  - `--test-paths/-p`
  - `--output-dir/-o`
  - `--env-file/-e`
  - `--env-manager-path`
  - `--with-langfuse/-l`

### Subcommands
- **test_quick_eval**: Quick evaluation without reference data
- **test_validate_external**: External agent validation
- **test_validate_native**: Native agent validation
- **test_red_teaming**: Red teaming attack generation and execution
- **test_generate**: Test case generation
- **test_analyze**: Result analysis
- **test_record**: Chat recording
- **test_environment_manager**: Environment manager and TestCaseManager functionality

## Adding New Tests

1. Add test methods to existing test classes, or
2. Create new test classes in the appropriate subdirectory
3. Use shared fixtures from `conftest.py`
4. Follow the naming convention: `test_<feature_name>`

## Notes

- All tests use mocking to avoid actual API calls
- The `USE_LEGACY_EVAL` flag tests reload the controller module to pick up environment variable changes
- Tests are isolated and can run in any order