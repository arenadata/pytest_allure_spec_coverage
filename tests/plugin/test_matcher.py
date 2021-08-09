# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests of ScenariosMatcher"""
# pylint: disable=redefined-outer-name

from dataclasses import dataclass, field
from typing import Collection, List, MutableSequence, Optional, Tuple, Type

import allure
import pytest
from _pytest.pytester import Pytester

from pytest_allure_spec_coverage.matcher import ScenariosMatcher, make_allure_labels
from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Parent, Scenario

from .common import run_with_allure


@pytest.fixture()
def scenarios() -> List[Scenario]:
    """List of fake scenarios assumed as returned by Collector instance"""

    return [
        Scenario(
            id="simple_scenario",
            name="simple_scenario",
            display_name="Simple scenario",
            parents=[
                Parent(name="scenarios", display_name="There is some scenarios"),
            ],
            link="link://simple_scenario",
            branch=None,
        ),
        Scenario(
            id="nested/scenario",
            name="nested_scenario",
            display_name="Nested scenario",
            parents=[
                Parent(name="scenarios", display_name="There is some scenarios"),
                Parent(name="nested", display_name="Nested"),
            ],
            link="link://nested_scenario",
            branch=None,
        ),
        Scenario(
            id="should_not_be_used",
            name="should_not_be_used",
            display_name="Should not be used",
            parents=[
                Parent(name="scenarios", display_name="There is some scenarios"),
            ],
            link="link://should_not_be_used",
            branch=None,
        ),
    ]


@dataclass
class TestCase:
    """Test case entry"""

    name: str
    matches: List[Scenario] = field(default_factory=list)


@pytest.fixture()
def test_cases(scenarios: List[Scenario]) -> Tuple[Collection[TestCase], Collection[Scenario]]:
    """Will return test cases collection alongside not implemented scenarios"""

    simple_scenario, nested_scenario, *not_implemented = scenarios

    return (
        TestCase("test_abandoned_case"),
        TestCase("test_non_existent_scenario_case"),
        TestCase("test_single_scenario_case", matches=[simple_scenario]),
        TestCase("test_multiple_scenarios_case", matches=[simple_scenario, nested_scenario]),
        TestCase("test_duplicated_scenarios_case", matches=[simple_scenario, simple_scenario]),
        TestCase("test_parametrized_case[1]", matches=[simple_scenario]),
        TestCase("test_parametrized_case[2]", matches=[simple_scenario]),
        TestCase("test_one_parameter_marked_only[1]"),
        TestCase("test_one_parameter_marked_only[2]", matches=[simple_scenario]),
    ), not_implemented


@pytest.fixture()
def collector_mock(scenarios: List[Scenario]) -> Type[Collector]:
    """Return Collector mock class"""

    class TestCollector(Collector):
        """Collector mock class"""

        def collect(self):
            return scenarios

        def setup_config(self):
            """Does not required"""

        @staticmethod
        def addoption(parser):
            """Does not required"""

    return TestCollector


@pytest.fixture()
def _conftest(pytester: Pytester, collector_mock: Type[Collector]) -> None:
    pytest.TestCollector = collector_mock
    conftest = """'''Register Collector mock'''
import pytest


def pytest_register_spec_collectors(collectors) -> None:
    collectors["test"] = pytest.TestCollector
    """
    pytester.makeconftest(conftest)


@pytest.fixture()
def custom_labels() -> Collection[str]:
    """Allure labels for specifications"""

    return "parentSpec", "spec", "subSpec"


@pytest.fixture()
def _pytestini(pytester: Pytester, custom_labels: Collection[str]) -> None:
    inifile = """# Register matcher options
[pytest]
allure_labels =
    """
    for label in custom_labels:
        inifile += f"\t{label}\n"
    pytester.makefile(".ini", pytest=inifile)


@allure.step("Check that case has no labels")
def _has_no_labels(case: dict, labels: Collection[str]) -> None:
    assert not [label["value"] for label in case["labels"] if label["name"] in labels]


@allure.step("Check that case has labels")
def _has_labels(case: dict, labels: Collection[str], values: Collection[str]) -> None:
    for label in make_allure_labels(labels, values):
        assert dict(name=label.name, value=label.value) in case["labels"]


@allure.step("Check that entry has link")
def _has_link(case: dict, needle: str) -> None:
    assert needle in [link["url"] for link in case["links"]]


@allure.step("Find entry {name}")
def _pop_result(results: MutableSequence[dict], name: str) -> Optional[dict]:
    for index, value in enumerate(results):
        if value["name"] == name:
            return results.pop(index)
    return None


def _has_result(results: MutableSequence[dict], name: str) -> dict:
    result = _pop_result(results, name)
    assert result, f"Case with name {name} not found"
    return result


@pytest.mark.usefixtures("_conftest", "_pytestini")
def test_matcher(
    pytester: Pytester,
    test_cases: Tuple[Collection[TestCase], Collection[Scenario]],
    scenarios: Collection[Scenario],
    custom_labels: Collection[str],
):
    """Test matcher"""

    cases, not_implemented = test_cases
    pytester_result, allure_results = run_with_allure(
        pytester=pytester,
        testfile_path="test_matcher.py",
        additional_opts=["--sc-type=test"],
        outcomes=dict(passed=len(cases)),
    )

    test_items = list(cases)
    fake_items = [
        TestCase(
            name=scenario.display_name,
            matches=[scenario],
        )
        for scenario in not_implemented
    ]

    with allure.step("Check actual test cases"):
        for item in test_items:
            result = _has_result(allure_results.test_cases, item.name)
            for match in item.matches:
                _has_link(result, match.link)
                _has_labels(result, custom_labels, match.specifications_names)
            if not item.matches:  # check that lables does not applied by mistake
                _has_no_labels(result, custom_labels)

    with allure.step("Check fake test cases"):
        for item in fake_items:
            result = _has_result(allure_results.test_cases, item.name)
            assert result["status"] == "unknown", "Unexpected entry status"
            for match in item.matches:
                _has_link(result, match.link)
                _has_labels(result, custom_labels, match.specifications_names)
                _has_labels(result, ScenariosMatcher.DEFAULT_LABELS, match.suites_names)

    assert not allure_results.test_cases, "Unexpected test cases reported"

    with allure.step("Check summary for coverage percent"):
        percent = (len(scenarios) - len(not_implemented)) * 100 // len(scenarios)
        assert f"{percent}%" in pytester_result.outlines[-1]
