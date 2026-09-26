from pytest_bdd import then, when
from pytest_bdd.parsers import re


@when(re(r"^I pick every ripe (?P<crop>\w+)$"))
def pick_ripe(crop):
    pass


@then(re(r"^the basket holds (?P<count>\d+) (?P<crop>\w+)$"))
def basket_holds(count, crop):
    pass
