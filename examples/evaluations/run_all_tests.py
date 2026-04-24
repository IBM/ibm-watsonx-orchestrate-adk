#!/usr/bin/env python3
"""
AgentOps Integration - Comprehensive Test Runner
This script runs all evaluation tests from the README and saves logs to output directories
"""

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from rich.console import Console
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        RichHandler(console=Console(width=150), rich_tracebacks=False, show_time=True)
    ],
)
logger = logging.getLogger(__name__)
script_dir = Path(__file__).parent.resolve()
ROOT_DIR = script_dir.parent.parent


class TestRunner:
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.tests = self._define_tests()

    def _define_tests(self) -> Dict[int, Dict[str, Any]]:
        """Define all test cases"""
        return {
            1: {
                "name": "Unit Tests",
                "commands": [
                    "pytest tests/cli/commands/evaluations/ -v --tb=short -rs"
                ],
                "output_dir": "./output/unit_tests",
                "skip": False,
            },
            2: {
                "name": "Help Commands",
                "commands": [
                    "orchestrate evaluations --help",
                    "orchestrate evaluations evaluate --help",
                    "orchestrate evaluations record --help",
                    "orchestrate evaluations generate --help",
                    "orchestrate evaluations analyze --help",
                    "orchestrate evaluations validate-external --help",
                    "orchestrate evaluations quick-eval --help",
                    "orchestrate evaluations red-teaming --help",
                ],
                "output_dir": "./output/help_commands",
                "skip": False,
            },
            3: {
                "name": "Evaluation (Legacy Mode)",
                "commands": [
                    "bash examples/evaluations/evaluate/import-all.sh",
                    "orchestrate evaluations evaluate -p ./examples/evaluations/evaluate/ -o ./output/eval -e .env",
                ],
                "output_dir": "./output/eval",
                "skip": False,
            },
            4: {
                "name": "Evaluation (Non-Legacy Mode)",
                "commands": [
                    "export USE_LEGACY_EVAL=FALSE",
                    "orchestrate evaluations evaluate -p examples/evaluations/evaluate/data_no_summary -o ./output/eval_non_legacy -l -e .env",
                    "export USE_LEGACY_EVAL=TRUE",
                ],
                "output_dir": "./output/eval_non_legacy",
                "skip": False,
            },
            5: {
                "name": "Evaluation with Context Variable",
                "commands": [
                    "bash examples/evaluations/evaluate_with_context_variable/import-all.sh",
                    "orchestrate evaluations evaluate -p examples/evaluations/evaluate_with_context_variable/ -o ./output/eval_context_var -e .env",
                ],
                "output_dir": "./output/eval_context_var",
                "skip": False,
            },
            6: {
                "name": "Evaluation with File Upload",
                "commands": [
                    "bash examples/evaluations/evaluate_with_file_upload/import-all.sh",
                    "orchestrate evaluations evaluate -p examples/evaluations/evaluate_with_file_upload/ -o ./output/eval_file_upload -e .env",
                ],
                "output_dir": "./output/eval_file_upload",
                "skip": False,
            },
            7: {
                "name": "Record Chat Sessions",
                "commands": [],
                "output_dir": "./output/record",
                "skip": True,
                "skip_reason": "Requires manual interaction. See README.md for details.",
            },
            8: {
                "name": "Generate Test Cases",
                "commands": [
                    "bash examples/evaluations/generate/import-all.sh",
                    "orchestrate evaluations generate -s examples/evaluations/generate/stories.csv -t examples/evaluations/generate/tools.py -o ./output/generate -e .env",
                ],
                "output_dir": "./output/generate",
                "skip": False,
            },
            9: {
                "name": "Analyze Results",
                "commands": [
                    "orchestrate evaluations analyze -d examples/evaluations/analysis/ -e .env",
                    "orchestrate evaluations analyze -d examples/evaluations/analysis/ -e .env -t examples/evaluations/analysis/tools.py",
                    "orchestrate evaluations analyze -d examples/evaluations/analysis/multi_run_example -t examples/evaluations/analysis/multi_run_example/tools.py",
                ],
                "output_dir": "./output/analyze",
                "skip": False,
            },
            10: {
                "name": "Red Teaming",
                "commands": [
                    "bash examples/evaluations/evaluate/import-all.sh",
                    "export USE_LEGACY_EVAL=TRUE && orchestrate evaluations red-teaming list",
                    "orchestrate evaluations red-teaming plan -a 'Crescendo Attack, Crescendo Prompt Leakage' -d examples/evaluations/evaluate/data_simple.json -g examples/evaluations/evaluate/agent_tools -t hr_agent -o ./output/red_team",
                    "orchestrate evaluations red-teaming run -a ./output/red_team -o ./output/red_team_run",
                ],
                "output_dir": "./output/red_team_run",
                "skip": False,
            },
            11: {
                "name": "Native Agent Validation",
                "commands": [
                    "export USE_LEGACY_EVAL=TRUE && orchestrate evaluations validate-native -t ./examples/evaluations/native_agent_validation/native_agent_validation.tsv -o ./output/native_agent_validation",
                ],
                "output_dir": "./output/native_agent_validation",
                "skip": False,
            },
            12: {
                "name": "External Agent Validation",
                "commands": [
                    "export USE_LEGACY_EVAL=TRUE && orchestrate evaluations validate-external --tsv './examples/evaluations/external_agent_validation/test.tsv' --external-agent-config './examples/evaluations/external_agent_validation/sample_external_agent_config.json' --perf -o ./output/external_agent_validation",
                ],
                "output_dir": "./output/external_agent_validation",
                "skip": False,
            },
            13: {
                "name": "Quick Eval",
                "commands": [
                    "export USE_LEGACY_EVAL=TRUE && orchestrate evaluations quick-eval -p examples/evaluations/quick-eval/ -o ./output/quick_eval -e .env -t examples/evaluations/evaluate/agent_tools",
                ],
                "output_dir": "./output/quick_eval",
                "skip": False,
            },
        }

    def run_test(self, test_num: int) -> bool:
        """Run a specific test"""
        if test_num not in self.tests:
            logger.error(f"Test {test_num} does not exist")
            return False

        test = self.tests[test_num]

        logger.info(f"Test {test_num}: {test['name']}")
        logger.info(f"{'='*40}")

        # Create output directory
        output_dir = self.root_dir / test.get("output_dir", "")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create log file
        log_file = output_dir / "test_run.log"

        # Write test header to log file
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"=== Test #{test_num}: {test['name']} ===\n")
            # Check if test should be skipped
            if test.get("skip", False):

                f.write(f"Test skipped. Reason: {test.get('skip_reason')}\n")
                logger.warning(f"SKIPPED - {test.get('skip_reason')}")
                return True

        # Run all commands for this test
        success = True
        for cmd in test["commands"]:
            logger.info(f"Running: {cmd}")
            try:
                # Run command and capture output
                result = subprocess.run(
                    f"LC_ALL=en_US.UTF-8 {cmd} 2>&1 | tee -a {log_file}",
                    shell=True,
                    cwd=self.root_dir,
                    env={**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
                )

                if result.returncode != 0:
                    success = False
                    logger.warning(f"Command exited with code {result.returncode}")

            except Exception as e:
                success = False
                error_msg = f"Error running command: {e}"
                logger.error(error_msg)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\nERROR: {error_msg}\n")

        # Write test footer to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== Completed at: {datetime.now()} ===\n")

        logger.info(
            f"Test completed: {test['name']} (check logs at {log_file} for details)"
        )

        return success

    def run_all_tests(self):
        """Run all tests"""
        logger.info(f"AgentOps Integration Test Suite")

        # Check for .env file
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            logger.error(f".env file not found in {self.root_dir}.")
            return

        total_tests = len([t for t in self.tests.values() if not t.get("skip", False)])
        logger.info(f"Running {total_tests} tests...\n")

        for test_num in sorted(self.tests.keys()):
            self.run_test(test_num)

        logger.info(
            f"All outputs saved to: ./output/\nCheck individual test_run.log files in each output directory."
        )

    def list_tests(self):
        """List all available tests"""
        print("\nAvailable Tests:")
        for num, test in sorted(self.tests.items()):
            status = " (SKIPPED)" if test.get("skip", False) else ""
            print(f"  {num:2d} - {test['name']}{status}")


def main():
    parser = argparse.ArgumentParser(description="Run AgentOps evaluation tests")
    parser.add_argument(
        "-t", "--test", type=int, help="Run specific test number (1-13)"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List all available tests"
    )

    args = parser.parse_args()
    runner = TestRunner()

    if args.list:
        runner.list_tests()
    elif args.test:
        runner.run_test(args.test)
    else:
        runner.run_all_tests()


if __name__ == "__main__":
    main()
