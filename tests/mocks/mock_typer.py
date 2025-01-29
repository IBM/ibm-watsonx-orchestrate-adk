from unittest.mock import MagicMock


def get_mock_typer():
    add_typer = MagicMock()

    class MockTyper:
        def __init__(self, *args, **kwargs):
            pass

        def add_typer(self, *args, **kwargs):
            add_typer(*args, **kwargs)

    return MockTyper, add_typer