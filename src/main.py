import re
from collections import Counter
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

from config import settings
from flights.api import CachedFlightAPI, FlightAPIError
from log import logger

flight_api_sdk = CachedFlightAPI(token=settings.flight_api_token)

app = FastAPI()
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


@app.post("/flights", response_class=HTMLResponse)
async def fetch_flights(request: Request, flight_request: Annotated[FlightRequest, Form()]):
    try:
        countries = await flight_api_sdk.get_today_arrivals_countries(flight_request.airport_code)
        countries_count = Counter(country for country in countries)
        sorted_countries = countries_count.most_common()
        return templates.TemplateResponse("flights.html", {"request": request, "countries": sorted_countries})
    except FlightAPIError as e:
        if e.status_code:
            logger.error(f"Error occurred: {e.message} (Status Code: {e.status_code}): {e.details}")
        else:
            logger.error(f"Error occurred: {e.message}: {e.details}")

        error_message = "Something went wrong. Please try again later."
        return templates.TemplateResponse("error.html", {"request": request, "error_message": error_message})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
