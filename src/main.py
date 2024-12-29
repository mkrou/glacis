import re
from collections import Counter
from contextlib import asynccontextmanager
from typing import Annotated
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from pydantic import BaseModel, field_validator

from config import settings
from flights.api import FlightAPI, FlightAPIError
from log import logger

flight_api_sdk = FlightAPI(token=settings.flight_api_token)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class FlightRequest(BaseModel):
    airport_code: str

    @field_validator('airport_code')
    @classmethod
    def validate_airport_code(cls, value: str) -> str:
        if not re.fullmatch(r'^[A-Za-z]{3}$', value):
            raise ValueError("airport code must contain exactly 3 Latin letters")
        return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_message = "Invalid input:"
    for err in exc.errors():
        error_message += f" {err.get("msg")};"

    return templates.TemplateResponse("error.html", {"request": request, "error_message": error_message})

# Initially, I added caching at the adapter level to the API as a simple and quick replacement for a mock server.
# In the release version of the application, it makes more sense to cache already aggregated data.
# The data is cached for an hour in order, on the one hand, to avoid wasting extra API tokens on repeated requests,
# and on the other hand, to update the data frequently enough in case of flight changes, etc.
# In a real application, the invalidation strategy should be reviewed depending on the usage scenario.
@cache(expire=60 * 60)
async def get_flights(airport_code: str) -> list[tuple[str, int]]:
    countries = await flight_api_sdk.get_today_arrivals_countries(airport_code)
    countries_count = Counter(country for country in countries)
    return countries_count.most_common()


@app.post("/flights", response_class=HTMLResponse)
async def fetch_flights(request: Request, flight_request: Annotated[FlightRequest, Form()]):
    try:
        return templates.TemplateResponse("flights.html", {
            "request": request,
            "countries": await get_flights(flight_request.airport_code)
        })
    except FlightAPIError as e:
        if e.status_code:
            logger.error(f"Error occurred: {e.message} (Status Code: {e.status_code}): {e.details}")
        else:
            logger.error(f"Error occurred: {e.message}: {e.details}")

        error_message = "Something went wrong. Please try again later."
        return templates.TemplateResponse("error.html", {"request": request, "error_message": error_message})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
