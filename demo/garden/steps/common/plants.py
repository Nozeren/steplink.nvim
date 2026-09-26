from pytest_bdd import given, then, when
from pytest_bdd.parsers import re


@given(re(r'^I have (?P<state>enabled|disabled) the sprinkler "(?P<bed>[^"]+)"$'))
def toggle_sprinkler(state, bed):
    pass


@when(re(r"^I water the (?P<plant>\w+) with (?P<amount>.+)$"))
def water_plant(plant, amount):
    pass


@then(re(r"^the soil is (?P<soil>dry|damp|wet)$"))
def soil_is(soil):
    pass


@when(re(r"^I prune the roses$"))
def prune_roses():
    pass
