import typer
import webbrowser

chat_app = typer.Typer(no_args_is_help=True)

@chat_app.command(name="start")
def chat_start():
    url = "http://localhost:3000/chat-lite"
    webbrowser.open(url)
    print(f"Opening chat interface at {url}")

if __name__ == "__main__":
    chat_app()