# Greeting Phrases Reference

This file is bundled with the hello-skill as a reference document. The watsonx Orchestrate
runtime auto-discovers it and makes it available to the skill at execution time.

## Standard Greetings

- Hello, {name}! Welcome to watsonx Orchestrate.
- Hi {name}, great to have you here!
- Hey {name}! How can I help you today?
- Good to see you, {name}!
- Welcome, {name}!

## Formal Greetings

- Good day, {name}. How may I assist you?
- Greetings, {name}. Welcome to the platform.
- Welcome aboard, {name}. I am here to help.

## Notes

- `{name}` is replaced with the user's actual name by the `greet` function in `scripts/greet.py`.
- All phrases are suitable for professional enterprise contexts.
- This file is uploaded automatically when running `orchestrate skills import --dir`.
