# CustomerCare Tutorials

This folder contains step-by-step tutorials for getting started with the project and building your own customer care agents using MCP (Model Context Protocol).

## Tutorial Path

Follow these tutorials in order for the best learning experience:

### 1. [Installation Guide](Installation.md)
**Start here if you're new to the repository**

Learn how to:
- Install prerequisites (Node.js, npm, UV)
- Set up the MCP server
- Run the banking agent demo
- Test with different customer profiles

**Time:** 15-20 minutes

---

### 2. [Getting Started](GettingStarted.md)
**Understand the architecture and concepts**

Learn about:
- The purpose of this technology demonstrator
- Customer Care Agent (CCA) style and its benefits
- Repository architecture and components
- Key concepts: MCP protocol, context layers, widgets
- The banking example walkthrough
- How this differs from traditional chatbots and Watson Assistant

**Time:** 30-45 minutes

---

### 3. [Extending the Server](ExtendingTheServer.md)
**Add features to the banking example**

Learn how to:
- Add new tools to existing product lines
- Create new product lines (with complete loan example)
- Implement widget-based tools
- Add resources for contextual information
- Follow best practices for tool development

**Time:** 45-60 minutes

---

### 4. [Creating New Servers](CreatingNewServers.md)
**Build your own MCP server from scratch**

Learn how to:
- Set up a new Node.js/TypeScript project
- Implement the MCP protocol
- Define tools for your domain (insurance example)
- Manage context with global and local stores
- Configure the agent runtime
- Add advanced features: authentication, widgets, resources

**Time:** 1-2 hours

---

### 5. [Setting Up Knowledge](SettingUpKnowledge.md)
**Set up Knowledge to use in the banking agent**

Learn how to:
- Setup a local OpenSearch instance
- Register the machine learning model and create the pipelines
- Create the vector index
- Ingest document to be used as the knowledge content

**Time:** 15-20 minutes

---

### 6. [Setting Up BYO Knowledge](SettingUpBYOKnowledge.md)
**Set up BYO Knowledge to use in the banking agent**

Learn how to:
- Setup the banking agent demo to work with BYO Knowledge

**Time:** 15-20 minutes

---

## Quick Reference

### For Beginners
Start with tutorials 1 and 2 to understand the basics.

### For Developers Extending the Banking Example
Focus on tutorial 3 after completing tutorials 1 and 2.

### For Developers Building New Servers
Complete all tutorials, with special attention to tutorial 4.

### For Architects and Decision Makers
Read tutorial 2 (Getting Started) to understand the architecture and benefits.

## Additional Resources

After completing these tutorials, explore:

- **[Pattern Documentation](../)** - Detailed guides for specific patterns
  - [Unique Tools Per User](../UniqueToolsPerUser.md)
  - [Widgets](../Widgets.md)
  - [Transactions](../Transactions.md)
  - [Authentication](../Authentication.md)
  - And more...

- **[Reference Documentation](../reference/)** - Technical specifications
  - [Context Variables](../reference/Context.md)
  - [Model Visibility](../reference/ModelVisibility.md)
  - [Widget Response Types](../reference/WidgetResponseTypes.md)

- **[MCP Extensions](../specChanges/)** - Orchestrate-specific MCP extensions
  - [Global Tool Refresh](../specChanges/GlobalToolRefreshMetadata.md)
  - [Multiple Widgets Per Tool](../specChanges/MultipleWidgetsPerTool.md)
  - [Tool Chaining](../specChanges/ToolChainingMetadata.md)
  - [Welcome Tool](../specChanges/WelcomeToolMetadata.md)

## Getting Help

- **Code Examples**: Working implementations in `../../src/`
- **Configuration Examples**: Sample setups in `../../agent_runtime/examples/`
- **Inline Comments**: Detailed explanations throughout the codebase

## Contributing Feedback

This is a technology demonstrator. We welcome feedback on:
- Tutorial clarity and completeness
- Missing topics or examples
- Developer experience
- What would make adoption easier

Your input helps shape how this style evolves for Watson Orchestrate.