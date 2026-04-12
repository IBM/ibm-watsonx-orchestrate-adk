# watsonx Orchestrate Skills

This directory contains Skills for working with the IBM watsonx Orchestrate Agent Development Kit (ADK). These skills provide expert guidance and assistance for building watsonx Orchestrate solutions, customer care MCP servers, and business documentation.

## Available Skills

### wxo-builder
**Location:** `wxo-builder/SKILL.md`

Expert guidance for **generating watsonx Orchestrate native solutions** from SOPs or simple prompts. Covers:
- Generating complete wxO implementations from Standard Operating Procedures (SOPs)
- Transforming business requirements into agents, tools, flows, and knowledge bases
- Recommended workflow: Use `sop-builder` to create SOPs from BPMN/n8n/Langflow first, then use `wxo-builder` to generate wxO solutions
- Knowledge base providers (Milvus, AstraDB, Elasticsearch)
- Standard project structure and implementation patterns
- Document processing flows and workflow patterns
- Python tool and flow decorators
- Agent YAML configuration
- CLI import commands and best practices
- Complete examples from the ADK repository

### sop-builder
**Location:** `sop-builder/SKILL.md`

Expert guidance for building Standard Operating Procedures (SOPs) from workflow diagrams and specifications. Covers:
- Analyzing BPMN diagrams, Langflow JSON, n8n workflows
- Generating business-focused SOPs in plain language
- Business process flow diagrams with Mermaid
- Data requirements and custom logic documentation
- LLM prompts documentation
- Business procedure steps and decision points
- Exception handling and integration points
- Translation from technical to business language

### customercare-mcp-builder
**Location:** `customercare-mcp-builder/SKILL.md`

Expert guide for building production-ready MCP (Model Context Protocol) servers for customer care agents. Covers:
- Transaction patterns with two-step confirmation
- Direct response and hybrid response patterns
- Tool chaining and context management
- Widget types (confirmation, datetime, number, options, text)
- Three-layer context system (context variables, global store, local store)
- Welcome tool and authentication patterns
- Agent handoff and knowledge/RAG integration
- Localization and multi-channel support
- Complete reference implementations and specifications

## Using These Skills

### In Claude Desktop or Web

1. Navigate to the Skills section in Claude
2. Import the desired skill by selecting the appropriate SKILL.md file:
   - `wxo-builder/SKILL.md` - For watsonx Orchestrate development
   - `sop-builder/SKILL.md` - For SOP generation from workflows
   - `customercare-mcp-builder/SKILL.md` - For customer care MCP servers
3. The skill will be available in your conversations

### With the MCP Server

The watsonx Orchestrate MCP server includes tools to fetch skills:

```python
# List available skills
list_available_skills()

# Fetch a specific skill
fetch_skill("wxo-builder", "./my_skills")
fetch_skill("sop-builder", "./my_skills")
fetch_skill("customercare-mcp-builder", "./my_skills")
```

## Skill Structure

The skill follows the Skills format:
- **SKILL.md**: Main skill file with frontmatter (name, description)
- **examples.md**: Complete reference implementations and code examples
- **Frontmatter**: Contains skill metadata
- **Content**: Expert guidance, specifications, and best practices

## Resources
- **Skill Documentation**: `customercare-mcp-builder/SKILL.md`
- **Reference Examples**: `customercare-mcp-builder/references/examples.md`
- **wxo-builder**: `wxo-builder/SKILL.md`
- **sop-builder**: `sop-builder/SKILL.md`
- **IBM watsonx Orchestrate ADK**: https://github.com/IBM/ibm-watsonx-orchestrate-adk
- **MCP Server**: `packages/mcp-server/ibm_watsonx_orchestrate_mcp_server/`

## Support

For questions or issues:
- Review the skill documentation and examples
- Consult the IBM watsonx Orchestrate official documentation
- Open an issue in the IBM watsonx Orchestrate ADK repository