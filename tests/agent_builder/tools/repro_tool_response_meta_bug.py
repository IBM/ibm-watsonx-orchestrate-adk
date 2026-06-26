"""Reproduce the plain-content ToolResponse _meta bug before/after the fix.

Run this script against an environment with wxo-clients 2.13 installed.
Before the fix, it should fail with AttributeError when calling to_dict().
After the fix, it should print the serialized response.
"""
from ibm_watsonx_orchestrate.agent_builder.tools._internal.tool_response import ToolResponse


def main() -> None:
    response = ToolResponse(content={"result": "ok"})
    print("Constructed ToolResponse")
    print("Calling to_dict()...")
    print(response.to_dict())


if __name__ == "__main__":
    main()
