def greet(name: str) -> str:
    """
    Greet a user by name and highlight the watsonx Orchestrate UI behaviour
    when a skill is invoked.

    Args:
        name: The name of the user to greet.

    Returns:
        A personalised greeting that also points the user to the reasoning
        panel in the watsonx Orchestrate UI.
    """
    return (
        f"👋 Hello, {name}! Welcome to watsonx Orchestrate.\n\n"
        "💡 Tip: check the reasoning panel in the UI — you should see a log "
        "entry showing that a Skill was invoked to produce this response. "
        "That's the hello-skill in action!"
    )
