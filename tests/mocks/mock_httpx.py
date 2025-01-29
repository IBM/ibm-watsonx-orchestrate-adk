import json as jsonp


class MockResponse:
    status_code: int
    text: str

    def __init__(self, json=None, text='{}', status_code=200):
        self.status_code = status_code
        if json:
            self.text = jsonp.dumps(json)
        else:
            self.text = text


    def json(self):
        return jsonp.loads(self.text)

def get_mock_async_client(respond_with: MockResponse = None):
    requests = []

    class AsyncClient:
        async def __aenter__(self):
            return AsyncClient()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def __init__(self):
            pass

        async def request(self, *args, **kwargs):
            requests.append({'args': args, 'kwargs': kwargs})
            return respond_with or MockResponse()

    return AsyncClient, requests

