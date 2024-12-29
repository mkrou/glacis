# Flights by Country

## Description

The **Flights by Country** project allows you to explore the countries from which flights arrive at a specific airport. This application uses FastAPI to create a web interface and interacts with an external API to fetch flight data.

## Demo

A live demo of the project is available at [https://glacis.fly.dev/](https://glacis.fly.dev/). The application is hosted on [fly.io](https://fly.io/).

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/glacis.git
   cd glacis
   ```

2. Install the dependencies using `uv`:

   ```bash
   uv sync
   ```

3. Create a `.env` file and add your API token:

   ```plaintext
   FLIGHT_API_TOKEN=your_token
   ```

## Running the Application

To run the application, use the command:

   ```bash
   uv run src/main.py
   ```
The application will be available at `http://localhost:8000`.

## Technologies Used

- **FastAPI**: for building the web application.
- **httpx**: for making HTTP requests.
- **Jinja2**: for HTML templating.
- **Pydantic**: for data validation.
- **htmx**: for handling dynamic HTML interactions.
- **Pico CSS**: for styling the web interface.