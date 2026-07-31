# watsonx Orchestrate Skills

This directory contains Skills for working with the IBM watsonx Orchestrate Agent Development Kit (ADK). These skills provide expert guidance and assistance for the **end-to-end lifecycle of enterprise automation and agent solutions**—from business requirements, to SOPs, to watsonx Orchestrate (wxO) implementation, to post-build analysis and documentation.

---

## Important Notes on Using Skills

**Model Interpretation:** Skill outputs are subject to interpretation by different LLM models. For best results, use a **coding agent with access to a frontier model** (e.g., IBM Bob, Claude 4.5 Sonnet, GPT-5.5, or equivalent) when working with these skills, as coding agents have tool access and stronger reasoning capabilities for complex analysis and generation tasks.

**Using Skill Outputs:** All skill outputs (documentation, evaluations, implementations, analyses) are provided **as-is** and should be used as **guides and starting points** rather than treated as absolute or final deliverables. Different models may produce different results based on their interpretation. Review and validate all outputs in the context of your specific requirements and use cases.

---

## Overview

This skill set covers the complete journey of building enterprise AI agent solutions:

1. **solution-architect** - Transforms business problems into structured solution architectures with executive summaries, technical designs, and implementation roadmaps. Creates the foundation for SOP development.

2. **sop-builder** - Converts technical procedures and workflows (e.g., BPMN, Langflow, n8n) into business-readable Standard Operating Procedures with plain-language descriptions, Mermaid diagrams, and detailed process documentation.

3. **wxo-builder** - Implements production-ready watsonx Orchestrate solutions from SOPs or prompts, generating agents, tools, flows, and knowledge bases following ADK best practices and project structures.

4. **wxo-analyzer** - Reverse-engineers existing wxO projects to produce comprehensive documentation, relationship diagrams, and anti-pattern analysis across enterprise AI failure modes for auditing and onboarding.

5. **telemetry-analyzer** - Exports and analyzes agent telemetry traces from watsonx Orchestrate (OTel or Langfuse JSON) to produce structured bug reports with root-cause analysis, fix recommendations, and conversational flow reports.

Together, these skills create a **closed-loop system** for designing, building, documenting, maintaining, and debugging enterprise-grade watsonx Orchestrate solutions.

---

## Available Skills

### 1. solution-architect
**Location:** `solution-architect/SKILL.md`

Focuses on turning business problems into **clear, structured solution architectures**. It bridges business and technical perspectives by producing:

- Executive-friendly solution overviews
- Technical architecture and design patterns
- Implementation roadmaps and SOP-ready documentation

**Best for:** Early-stage design and alignment

**Key Capabilities:**
- Analyzing business requirements and problem statements
- Generating three focused architecture documents (Solution Overview, Technical Architecture, Implementation Plan)
- Business-focused summaries and context
- Bridging business needs with technical implementation
- Preparing documentation for elaboration into detailed SOPs
- Modular, manageable documentation structure

---

### 2. sop-builder
**Location:** `sop-builder/SKILL.md`

Transforms **technical workflows into business-readable SOPs**. It:

- Converts BPMN, Langflow, and n8n workflows into plain-language procedures
- Documents decision points, exceptions, integrations, and prompts
- Produces visuals (Mermaid) and business-ready process descriptions

**Best for:** Standardizing and operationalizing processes

**Key Capabilities:**
- Analyzing BPMN diagrams, Langflow JSON, n8n workflows
- Generating business-focused SOPs in plain language
- Business process flow diagrams with Mermaid
- Data requirements and custom logic documentation
- LLM prompts documentation
- Business procedure steps and decision points
- Exception handling and integration points
- Translation from technical to business language

---

### 3. wxo-builder
**Location:** `wxo-builder/SKILL.md`

Turns SOPs or prompts into **fully implemented watsonx Orchestrate solutions**. It:

- Generates agents, tools, flows, and knowledge bases
- Follows recommended ADK project structures and patterns
- Supports multiple KB backends and end-to-end CLI workflows

**Best for:** Implementation and production-ready wxO builds

**Key Capabilities:**
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

---

### 4. wxo-analyzer
**Location:** `wxo-analyzer/SKILL.md`

Reverse-engineers and documents existing **wxO projects**. It:

- Analyzes project structure and components
- Produces multi-report documentation (overview, agents, tools)
- Generates diagrams and relationship mappings
- Detects anti-patterns and provides recommendations

**Best for:** Understanding, auditing, or onboarding into existing wxO solutions

**Key Capabilities:**
- Analyzing existing wxO project structures
- Generating three-report documentation sets (Solution Overview, Agent Analysis, Tools & Components)
- Creating Mermaid diagrams showing component relationships
- Documenting agents, tools, connections, and knowledge bases
- Project structure and component inventory
- Relationship mapping between agents, tools, and resources
- Anti-pattern detection across 15 enterprise AI failure modes
- Instruction line counting and complexity analysis
- Production readiness assessment

---

### 5. agent-instructions-evaluator
**Location:** `agent-instructions-evaluator/SKILL.md`

Evaluates agent instructions and definitions for **operational achievability in production settings**. It:

- Analyzes runtime reliability rather than writing quality
- Identifies issues from hidden state, conflicting rules, vague scope, and brittle phrasing
- Produces structured evaluation reports with evidence-backed findings
- Provides per-dimension scores across 5 evaluation dimensions (0-5 scale)

**Best for:** Validating agent instructions before deployment and identifying production failure risks

**Key Capabilities:**
- Evaluating agent instructions across 5 dimensions (Task Understanding, Scope & Applicability, Execution & Tool Grounding, Instruction Followability, State & Conflict Manageability)
- Deterministic signal counting (exact phrases, nested branches, implicit state)
- Evidence-backed findings with impact analysis and recommendations
- Risk prioritization and high-leverage improvement identification
- Structured JSON output for evaluation harnesses
- Support for watsonx Orchestrate YAML, system prompts, and agent definitions
- Production readiness assessment focused on runtime reliability

---

### 6. telemetry-analyzer
**Location:** `telemetry-analyzer/SKILL.md`

Exports and analyzes **agent telemetry traces** from watsonx Orchestrate to identify bugs, failures, and inefficiencies. It:

- Supports OTel JSON (ADK `TracesController` / local IBM telemetry) and Langfuse JSON (agentops-v3 REST API)
- Detects trace format automatically, normalizes spans, and scans for errors
- Produces structured HTML bug reports and thread-scoped conversational flow reports

**Best for:** Debugging misbehaving agents and understanding production failures from telemetry data

**Key Capabilities:**
- Identifying trace source (remote wxO API, agentops-v3 REST API, local IBM telemetry, or files already on disk)
- Exporting traces by agent name or ID via ADK `TracesController` or `export_traces_agentops_v3.py`
- Format detection and normalization across OTel and Langfuse JSON schemas
- Detecting hard errors, LLM failures, tool call failures, agent logic bugs, flow/widget issues, token anomalies, and cache inefficiency
- Structured HTML bug reports with executive summary, trace summary table, issues, warnings, and fix recommendations
- Conversational flow reports reconstructing multi-turn threads from thread-scoped traces

---

### 7. customercare-mcp-builder
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

**Best for:** Building customer care MCP servers with rich UI interactions

---

## How They Fit Together

A typical end-to-end workflow looks like:

```
Business Problem
      ↓
[solution-architect] → Solution Architecture Documents
      ↓
[sop-builder] → Standard Operating Procedures
      ↓
[wxo-builder] → watsonx Orchestrate Implementation
      ↓
[wxo-analyzer] → Documentation & Anti-Pattern Analysis
      ↓
[telemetry-analyzer] → Bug Reports & Fix Recommendations
```

This creates a **closed-loop system** where:
1. **solution-architect** establishes the foundation and high-level design
2. **sop-builder** creates detailed, business-readable procedures
3. **wxo-builder** implements the technical solution
4. **wxo-analyzer** validates, documents, and identifies improvements
5. **telemetry-analyzer** debugs production issues from live telemetry traces

---

## Using These Skills

### In Claude Desktop or Web

1. Navigate to the Skills section in Claude
2. Import the desired skill by selecting the appropriate SKILL.md file:
   - `solution-architect/SKILL.md` - For solution architecture documentation
   - `sop-builder/SKILL.md` - For SOP generation from workflows
   - `wxo-builder/SKILL.md` - For watsonx Orchestrate development
   - `wxo-analyzer/SKILL.md` - For analyzing existing wxO projects
   - `agent-instructions-evaluator/SKILL.md` - For evaluating agent instructions
   - `customercare-mcp-builder/SKILL.md` - For customer care MCP servers
   - `telemetry-analyzer/SKILL.md` - For analyzing agent telemetry traces
3. The skill will be available in your conversations

### With the MCP Server

The watsonx Orchestrate MCP server includes tools to fetch skills:

```python
# List available skills
list_available_skills()

# Fetch a specific skill
fetch_skill("solution-architect", "./my_skills")
fetch_skill("sop-builder", "./my_skills")
fetch_skill("wxo-builder", "./my_skills")
fetch_skill("wxo-analyzer", "./my_skills")
fetch_skill("agent-instructions-evaluator", "./my_skills")
fetch_skill("customercare-mcp-builder", "./my_skills")
fetch_skill("telemetry-analyzer", "./my_skills")

# Fetch all skills at once
fetch_all_skills("./my_skills")
```

---

## Skill Structure

Each skill follows the Skills format:
- **SKILL.md**: Main skill file with frontmatter (name, description)
- **examples.md**: Complete reference implementations and code examples (where applicable)
- **Frontmatter**: Contains skill metadata
- **Content**: Expert guidance, specifications, and best practices

---

## Resources

- **solution-architect**: `solution-architect/SKILL.md`
- **sop-builder**: `sop-builder/SKILL.md`
- **wxo-builder**: `wxo-builder/SKILL.md`
- **wxo-analyzer**: `wxo-analyzer/SKILL.md`
- **agent-instructions-evaluator**: `agent-instructions-evaluator/SKILL.md`
- **customercare-mcp-builder**: `customercare-mcp-builder/SKILL.md`
- **telemetry-analyzer**: `telemetry-analyzer/SKILL.md`
- **Reference Examples**: `customercare-mcp-builder/references/examples.md`
- **IBM watsonx Orchestrate ADK**: https://github.com/IBM/ibm-watsonx-orchestrate-adk
- **MCP Server**: `packages/mcp-server/ibm_watsonx_orchestrate_mcp_server/`

---

## Support

For questions or issues:
- Review the skill documentation and examples
- Consult the IBM watsonx Orchestrate official documentation
- Open an issue in the IBM watsonx Orchestrate ADK repository