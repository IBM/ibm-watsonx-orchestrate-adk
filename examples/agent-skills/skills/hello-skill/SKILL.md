---
name: hello-skill
description: Greet a user by name and demonstrate the watsonx Orchestrate skills surface.
---

# Hello Skill

It greets a user by name.

## What this skill does

- Accepts a user's name and returns a personalised greeting

## When to use

Invoke this skill when the agent needs to:

- Greet a user by name at the start of a conversation

## Example invocations

```
Say hello to Alice
Greet my colleague Sam
Welcome Jordan to the platform
```

## Reference data

The file `references/resource.md` lists supported greeting phrases the skill can draw from.
The runtime auto-discovers and makes this file available at execution time.

## Script

The file `scripts/greet.py` defines a plain Python function `greet(name: str) -> str`
that is uploaded to the skill runtime and called by the agent when a greeting is needed.

| Function | Input | Output |
|----------|-------|--------|
| `greet` | `name: str` | Personalised greeting with a UI tip pointing to the reasoning panel |
