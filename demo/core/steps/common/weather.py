from pytest_bdd import given
from pytest_bdd.parsers import re


@given(re(r"^it is (?P<weather>sunny|raining)$"))
def the_weather(weather):
    return weather
