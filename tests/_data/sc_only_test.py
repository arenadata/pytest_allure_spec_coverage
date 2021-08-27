"""Tests for --sc-only option tests"""
import pytest


def test_abandoned_case():
    """Case without scenario mark"""


@pytest.mark.scenario("simple_scenario")
def test_single_scenario_case():
    """Case with the single one scenario"""


@pytest.mark.scenario("deselected_scenario")
def test_deselected_scenario_case():
    """Case that will be deselected but covered scenario"""
