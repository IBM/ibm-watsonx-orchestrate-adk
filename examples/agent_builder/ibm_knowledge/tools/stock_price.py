from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def get_stock_price(stock_symbol_list: list[str]):
    """
    Retrieve stock price given a list of stock symbols.

    Returns:
      A dictionary in the format of {SYMBOL: price}
    """
    fake_stock_price = {
        'AAPL': 100.0,
        'META': 101.0,
        'CSCO': 102.0,
        'UAA': 103.0,
        'UA': 104.0,
        'BOX': 105.0,
        'MSFT': 106.0,
        'M': 107.0,
        'CRM': 108.0,
        'AMZN': 109.0,
    }

    return {s: fake_stock_price[s] for s in stock_symbol_list if s in fake_stock_price}
