import json
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
from openai import AsyncOpenAI
from pydantic import BaseModel, field_validator

from config import settings
from log import logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="src/templates")
client = AsyncOpenAI(api_key=settings.openai_api_key)
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


tools = [{
    "type": "function",
    "function": {
        "name": "query_flights",
        "description": """
        Query flights to a specific airport. 
        
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """The correct pandas text query to filter the flight data. Available fields: 
        - destination_airport = 3-letter airport code
        - src_airline_code = 2-letter airline code
        - src_country = country full name in English
        - src_city = city full name in English
        - src_identification_codeshare = codeshare code
        - flight_number = flight number
        - Arrived Late = boolean
        - Estimated Late = boolean"""},
            },
            "required": ["query"],
            "additionalProperties": False
        },
        "strict": True
    }
}]


def query_flights(airport_code: str, query: str) -> pd.DataFrame:
    """
    Query the flight data for flights to a specific airport and further filter based on a text query.

    :param airport_code: The destination airport code to filter by.
    :param query: The text query to further filter the flight data.
    :return: A DataFrame containing the filtered flight data.
    """
    logger.info(f"Querying flights for {airport_code} with query: {query}")
    filtered_df = flight_data_df[flight_data_df['destination_airport'] == airport_code]
    filtered_df = filtered_df.query(query)
    return filtered_df


@app.post("/flights", response_class=HTMLResponse)
async def fetch_flights(request: Request, flight_request: Annotated[FlightRequest, Form()]):
    try:
        prompt = f"""
        You are an expert in flight data. 
        Always answer in the same language as the question. 
        You are answering only on questions about flights to selected {flight_request.airport_code} airport.
        If the question is not about flights to {flight_request.airport_code} airport, ask to choose another airport.
        Build just one query to filter the flight data based on the question.
        Question: {flight_request.question}
        """

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": flight_request.question}
        ]

        completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools
        )

        if completion.choices[0].message.tool_calls:
            tool_call = completion.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            data = query_flights(flight_request.airport_code, args["query"])
            messages.append(completion.choices[0].message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": data.to_string()
            })

            completion = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
            )

        return templates.TemplateResponse("flights.html", {
            "request": request,
            "response": completion.choices[0].message.content
        })

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")

        error_message = "Something went wrong. Please try again later."
        return templates.TemplateResponse("error.html", {"request": request, "error_message": error_message})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
