from unittest.mock import MagicMock


def get_mock_typer():
    add_typer = MagicMock()
    add_command = MagicMock()

    class MockTyper:
        def __init__(self, *args, **kwargs):
            pass

        def add_typer(self, *args, **kwargs):
            add_typer(*args, **kwargs)

        def command(self, *args, **kwargs):
            return add_command(*args, **kwargs)

    return MockTyper, add_typer, add_command