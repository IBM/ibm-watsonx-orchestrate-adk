"""
Text extraction flow builder example.

This module demonstrates how to build, compile, deploy, and invoke
a document processing flow for text extraction.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# This is the flow that we will run. Change the selected flow to run other flows.
from examples.flow_builder.text_extraction.tools.text_extraction_flow import (
    build_docproc_flow,
)

# Configure logging with appropriate format and level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class FlowExecutor:
    """Encapsulates flow execution logic and state management."""

    def __init__(self, document_ref: str, kvp_schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the flow executor.

        Args:
            document_ref: Reference to the document to process.
            kvp_schema: Optional KVP schema dictionary to pass to the flow.
        """
        self.document_ref = document_ref
        self.kvp_schema = kvp_schema
        self.flow_run: Optional[Any] = None

    def on_flow_end(self, result: Any) -> None:
        """
        Callback function invoked when the flow completes successfully.

        Args:
            result: The result returned by the flow execution.
        """
        if self.flow_run:
            logger.info(
                "Flow '%s' completed successfully with result:\n%s",
                self.flow_run.name,
                result,
            )
        else:
            logger.warning("Flow completed but flow_run is not set")

    def on_flow_error(self, error: Exception) -> None:
        """
        Callback function invoked when the flow encounters an error.

        Args:
            error: The exception that caused the flow to fail.
        """
        if self.flow_run:
            logger.error(
                "Flow '%s' failed with error: %s",
                self.flow_run.name,
                error,
                exc_info=True,
            )
        else:
            logger.error("Flow failed: %s", error, exc_info=True)

    async def execute(self) -> None:
        """
        Build, compile, deploy, and invoke the document processing flow.

        Raises:
            Exception: If flow compilation, deployment, or invocation fails.
        """
        try:
            logger.info("Building document processing flow...")
            my_flow_definition = await build_docproc_flow().compile_deploy()

            # Use Path for cross-platform compatibility
            generated_folder = Path(__file__).resolve().parent / "generated"
            generated_folder.mkdir(parents=True, exist_ok=True)

            spec_path = generated_folder / "docproc_flow.json"
            logger.info("Saving flow specification to: %s", spec_path)
            my_flow_definition.dump_spec(str(spec_path))

            logger.info("Invoking flow with document reference: %s", self.document_ref)

            # Build input data with document_ref
            input_data: Dict[str, Any] = {"document_ref": self.document_ref}
            
            # Add kvp_schemas if provided
            if self.kvp_schema:
                input_data["kvp_schemas"] = [self.kvp_schema]
                logger.info("Added KVP schema to flow input")

            self.flow_run = await my_flow_definition.invoke(
                input_data=input_data,
                on_flow_end_handler=self.on_flow_end,
                on_flow_error_handler=self.on_flow_error,
                debug=True,
            )

        except Exception as e:
            logger.error("Failed to execute flow: %s", e, exc_info=True)
            raise


def load_kvp_schema(schema_path: str) -> Dict[str, Any]:
    """
    Load KVP schema from a JSON file.

    Args:
        schema_path: Path to the JSON schema file.

    Returns:
        The loaded schema as a dictionary.

    Raises:
        SystemExit: If the file cannot be read or parsed.
    """
    try:
        schema_file = Path(schema_path)
        if not schema_file.exists():
            logger.error("KVP schema file not found: %s", schema_path)
            print(f"Error: KVP schema file not found: {schema_path}", file=sys.stderr)
            sys.exit(1)

        with schema_file.open("r", encoding="utf-8") as f:
            schema = json.load(f)
            logger.info("Successfully loaded KVP schema from: %s", schema_path)
            return schema

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in KVP schema file: %s", e)
        print(f"Error: Invalid JSON in KVP schema file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to load KVP schema: %s", e)
        print(f"Error: Failed to load KVP schema: {e}", file=sys.stderr)
        sys.exit(1)


def validate_arguments() -> tuple[str, Optional[Dict[str, Any]]]:
    """
    Validate command-line arguments.

    Returns:
        A tuple of (document_ref, kvp_schema) where kvp_schema is None if not provided.

    Raises:
        SystemExit: If arguments are invalid.
    """
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        logger.error("Invalid number of arguments provided")
        print(
            "Usage: python main.py <document_ref> [kvp_schema_path]\n"
            "  document_ref: Reference to the document to process\n"
            "  kvp_schema_path: (Optional) Path to JSON file containing KVP schema\n"
            "Please follow README for detailed instructions.",
            file=sys.stderr,
        )
        sys.exit(1)

    document_ref = sys.argv[1].strip()
    if not document_ref:
        logger.error("Document reference cannot be empty")
        print("Error: Document reference cannot be empty", file=sys.stderr)
        sys.exit(1)

    kvp_schema = None
    if len(sys.argv) == 3:
        kvp_schema_path = sys.argv[2].strip()
        if kvp_schema_path:
            kvp_schema = load_kvp_schema(kvp_schema_path)
        else:
            logger.warning("KVP schema path provided but is empty, ignoring")

    return document_ref, kvp_schema


async def main() -> None:
    """
    Main entry point for the text extraction flow example.

    Validates arguments, initializes the flow executor, and runs the flow.
    """
    try:
        document_ref, kvp_schema = validate_arguments()
        executor = FlowExecutor(document_ref, kvp_schema)
        await executor.execute()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.critical("Unhandled exception in main: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
