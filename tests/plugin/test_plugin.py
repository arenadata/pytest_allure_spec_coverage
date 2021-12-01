"""
Test common plugin behaviour
"""
from _pytest.pytester import Pytester

from tests.plugin.common import run_with_allure


def test_skip_if_testplan_exists(pytester: Pytester, monkeypatch):
    """
    Test that plugin is disabled if allure testplan exists
    """
    monkeypatch.setenv("ALLURE_TESTPLAN_PATH", "testplan.json")
    opts = ["--sc-type", "something"]
    pytester_result, _ = run_with_allure(
        pytester=pytester,
        testfile_path="simple_test.py",
        additional_opts=opts
    )
    assert 'Spec coverage plugin is disabled due to allure testplan exists' in pytester_result.outlines
