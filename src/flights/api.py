from typing import Any

import httpx
from jsonpath_ng import parse

ARRIVALS_JSONPATH = '$[*].airport.pluginData.schedule.arrivals.data[*].flight.airport.origin.position.country.name'


class FlightAPIError(Exception):
    """
    General exception for FlightAPI errors.
    """

    def __init__(self, message: str, status_code: int | None = None, details: str | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class FlightAPI:
    """
    SDK for interacting with the FlightAPI.
    """

    def __init__(self, token: str):
        """
        Initializes the SDK with the provided token.

        :param token: API authentication token.
        """
        self.base_url = "https://api.flightapi.io"
        self.token = token

    async def get_today_arrivals_countries(self, airport_code: str) -> list[str]:
        """
        Fetches the flight schedule.

        :param airport_code: Airport IATA code.
        :return: API response in JSON format.
        """

        params = {
            "mode": "arrivals",
            "iata": airport_code,
            "day": 1,
        }
        result = await self._make_request("compschedule", params=params)
        jsonpath_expr = parse(ARRIVALS_JSONPATH)
        return [match.value for match in jsonpath_expr.find(result)]

    async def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Makes a request to the API.

        :param endpoint: API endpoint.
        :param params: Optional query parameters.
        :return: API response in JSON format.
        """

        url = f"{self.base_url}/{endpoint}/{self.token}"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise FlightAPIError(
                message="HTTP error occurred",
                status_code=e.response.status_code,
                details=e.response.text
            ) from e
        except Exception as e:
            raise FlightAPIError(
                message="An unexpected error occurred",
                details=e.__class__.__name__ + str(e)
            ) from e


class CachedFlightAPI(FlightAPI):
    """
    A version of FlightAPI that caches results in memory.
    """

    def __init__(self, token: str):
        """
        Initializes the SDK with the provided token and an empty cache.

        :param token: API authentication token.
        """
        super().__init__(token)
        self._cache: dict[str, list[str]] = {}

    async def get_today_arrivals_countries(self, airport_code: str) -> list[str]:
        """
        Fetches the flight schedule with caching.

        :param airport_code: Airport IATA code.
        :return: List of origin countries for today's arrivals.
        """

        if airport_code in self._cache:
            return self._cache[airport_code]

        countries = await super().get_today_arrivals_countries(airport_code)
        self._cache[airport_code] = countries
        return countries
