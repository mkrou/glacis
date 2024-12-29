import json

from jsonpath_ng.ext import parse

from src.flights.api import ARRIVALS_JSONPATH


def test_jsonpath_extraction():
    jsonpath_expr = parse(ARRIVALS_JSONPATH)

    with open("tests/data/arrivals.json") as arrivals_raw:
        arrivals = json.load(arrivals_raw)

    extracted_countries = [match.value for match in jsonpath_expr.find(arrivals)]

    expected_countries = ["India", "Thailand"]

    assert extracted_countries == expected_countries, f"Expected {expected_countries}, but got {extracted_countries}"
