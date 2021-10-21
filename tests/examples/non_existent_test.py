"""Non-existent scenario"""
import pytest


@pytest.mark.scenario("non_existent")
def test_non_existent_scenario_case():
    """Case implemented non-existent scenario"""


@pytest.mark.scenario("simple_scenario")
def test_single_scenario_case():
    """Case with the single one scenario"""
