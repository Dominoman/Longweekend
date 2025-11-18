from datetime import datetime, date
from typing import Dict, Any

import requests


class Tequila:
    """
    Tequila class for interacting with the Kiwi flight search API.

    The Tequila class provides methods to search for flights using the Kiwi API.

    Methods:
        - search: Searches for flights based on the provided parameters.

    For method details, refer to the individual method docstrings.
    """

    def __init__(self, apikey: str) -> None:
        """
        Initializes a Kiwi object with the provided API key.

        Args:
            apikey (str): The API key to access the Kiwi API.

        Returns:
            None
        """
        self.apikey = apikey
        self.status_code = 0
        self.search_url = ""

    def search(self, fly_from: str, date_from: date, date_to: date, fly_to: str = None,
               nights_in_dst_from: int = None, nights_in_dst_to: int = None, curr: str = "HUF", locale: str = "hu",
               **kwargs) -> Dict[str, Any]:
        """
        Searches for flights based on the provided parameters.

        Args:
            fly_from (str): The IATA code of the departure airport.
            date_from (datetime): The start date for the flight search.
            date_to (datetime): The end date for the flight search.
            fly_to (str, optional): The IATA code of the destination airport. Defaults to None.
            nights_in_dst_from (int, optional): Minimum nights at the destination. Defaults to None.
            nights_in_dst_to (int, optional): Maximum nights at the destination. Defaults to None.
            curr (str, optional): The currency code. Defaults to "HUF".
            locale (str, optional): The locale for the response. Defaults to "hu".
            **kwargs: Additional keyword arguments for the search.

        Returns:
            dict: A dictionary containing the JSON response from the flight search API.
        """

        params = {"fly_from": fly_from, "fly_to": fly_to, "date_from": f"{date_from:%d/%m/%Y}",
                   "date_to": f"{date_to:%d/%m/%Y}", "nights_in_dst_from": nights_in_dst_from,
                   "nights_in_dst_to": nights_in_dst_to, "curr": curr, "locale": locale, **kwargs}
        filtered = {k: v for k, v in params.items() if v is not None}
        response = requests.get("https://api.tequila.kiwi.com/v2/search", params=filtered,
                                headers={"apikey": self.apikey})
        self.status_code = response.status_code
        self.search_url = response.url
        return response.json()

