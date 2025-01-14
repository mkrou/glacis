import re
from contextlib import asynccontextmanager
from typing import Annotated
from typing import AsyncIterator

import pandas as pd
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from pandasai import SmartDataframe
from pandasai.llm import OpenAI
from pydantic import BaseModel, field_validator

from config import settings
from log import logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="src/templates")
llm = OpenAI(api_token=settings.openai_api_key)
flight_data_df = pd.read_json('assets/flight_data.json')


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    AIRPORTS = ["DXB", "LHR", "CDG", "SIN", "HKG", "AMS"]

    return templates.TemplateResponse("index.html", {"request": request, "airports": AIRPORTS})


class FlightRequest(BaseModel):
    airport_code: str
    question: str

    @field_validator('airport_code')
    @classmethod
    def validate_airport_code(cls, value: str) -> str:
        if not re.fullmatch(r'^[A-Za-z]{3}$', value):
            raise ValueError("airport code must contain exactly 3 Latin letters")
        return value

    @field_validator('question')
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not (5 <= len(value.strip()) <= 300):
            raise ValueError("question must be between 3 and 300 characters")
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
        flight_data_subset_df = flight_data_df[flight_data_df['destination_airport'] == flight_request.airport_code]

        smart_flight_data_df = SmartDataframe(flight_data_subset_df, config={"llm": llm})

        prompt = f"""
        You are an expert in flight data. 
        Always answer in the same language as the question. 
        You are answering only on questions about flights to {flight_request.airport_code} airport.
        Question: {flight_request.question}
        """

        return templates.TemplateResponse("flights.html", {
            "request": request,
            "response": smart_flight_data_df.chat(prompt, output_type="string")
        })

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")

        error_message = "Something went wrong. Please try again later."
        return templates.TemplateResponse("error.html", {"request": request, "error_message": error_message})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
