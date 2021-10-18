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

from contextlib import contextmanager
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Collection, Generator, List, MutableSequence, Optional, Tuple

import allure
import allure_commons
import pytest
from _pytest.config import ExitCode
from _pytest.fixtures import SubRequest
from _pytest.pytester import Pytester

from pytest_allure_spec_coverage.common import allure_listener
from pytest_allure_spec_coverage.matcher import ScenariosMatcher, make_allure_labels
from pytest_allure_spec_coverage.models.scenario import Scenario
from .common import run_tests, run_with_allure
from ..examples.collector import scenarios


@dataclass
class TestCase:
    """Test case entry"""

    name: str
    matches: List[Scenario] = field(default_factory=list)
    status: str = "unknown"


def test_cases() -> Tuple[Collection[TestCase], Collection[Scenario], Collection[Scenario]]:
    """Will return test cases collection alongside not implemented scenarios"""

    simple_scenario, nested_scenario, deselected_scenario, *not_implemented = scenarios

    return (
        (
            TestCase("test_abandoned_case"),
            TestCase("test_non_existent_scenario_case"),
            TestCase("test_single_scenario_case", matches=[simple_scenario]),
            TestCase("test_multiple_scenarios_case", matches=[simple_scenario, nested_scenario]),
            TestCase("test_duplicated_scenarios_case", matches=[simple_scenario, simple_scenario]),
            TestCase("test_parametrized_case[1]", matches=[simple_scenario]),
            TestCase("test_parametrized_case[2]", matches=[simple_scenario]),
            TestCase("test_one_parameter_marked_only[1]"),
            TestCase("test_one_parameter_marked_only[2]", matches=[simple_scenario]),
        ),
        [deselected_scenario],
        not_implemented,
    )


@pytest.fixture()
def _conftest(pytester: Pytester) -> None:
    pytester.copy_example("collector.py")
    conftest = """
    '''Register Collector mock'''
    from collector import CollectorMock


    def pytest_register_spec_collectors(collectors) -> None:
        collectors["test"] = CollectorMock
    """
    pytester.makeconftest(dedent(conftest))


@pytest.fixture()
def custom_labels() -> Collection[str]:
    """Allure labels for specifications"""

    return "parentSpec", "spec", "subSpec"


@pytest.fixture()
def _pytestini(pytester: Pytester, custom_labels: Collection[str]) -> None:
    inifile = dedent(
        """
    # Register matcher options
    [pytest]
    allure_labels =
    """
    )
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


@contextmanager
def allure_unloaded(request: SubRequest) -> Generator:  # pylint: disable=inconsistent-return-statements
    """Unload AllureListener plugin"""

    manager = allure_commons.plugin_manager.get_plugin_manager()
    listener = allure_listener(request.config)
    if not listener:
        return (yield)

    manager.unregister(listener)
    yield
    manager.register(listener)


@pytest.mark.usefixtures("_conftest", "_pytestini")
@pytest.mark.parametrize("xdist", [True, False], ids=["xdist", "in_series"])
def test_matcher(
    xdist: bool,
    pytester: Pytester,
    custom_labels: Collection[str],
):
    """Test matcher"""

    cases, deselected, not_implemented = test_cases()
    opts = ["--sc-type", "test", "-k", "not deselected"]
    if xdist:
        opts.extend(["-n", "2"])
    pytester_result, allure_results = run_with_allure(
        pytester=pytester,
        testfile_path="matcher_pytester_test.py",
        additional_opts=opts,
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
    fake_items.extend([TestCase(name=scenario.display_name, status="skipped") for scenario in deselected])

    with allure.step("Check actual test cases"):
        for item in test_items:
            result = _has_result(allure_results.test_cases, item.name)
            for match in item.matches:
                _has_link(result, match.link)
                _has_labels(result, custom_labels, match.specifications_names)
            if not item.matches:  # check that labels does not applied by mistake
                _has_no_labels(result, custom_labels)

    with allure.step("Check fake test cases"):
        for item in fake_items:
            result = _has_result(allure_results.test_cases, item.name)
            assert result["status"] == item.status, "Unexpected entry status"
            for match in item.matches:
                _has_link(result, match.link)
                _has_labels(result, custom_labels, match.specifications_names)
                _has_labels(result, ScenariosMatcher.DEFAULT_LABELS, match.suites_names)

    assert not allure_results.test_cases, "Unexpected test cases reported"

    with allure.step("Check summary for coverage percent"):
        percent = (len(scenarios) - len(not_implemented)) * 100 // len(scenarios)
        assert any(
            f"{percent}%" in outline for outline in pytester_result.outlines
        ), f'Should be "{percent}%" in outlines'


@pytest.mark.usefixtures("_conftest")
def test_matcher_without_allure(
    request: SubRequest,
    pytester: Pytester,
):
    """Test matcher without allure"""

    *_, not_implemented = test_cases()
    percent = (len(scenarios) - len(not_implemented)) * 100 // len(scenarios)
    with allure_unloaded(request):
        pytester_result = run_tests(
            pytester=pytester,
            testfile_path="matcher_pytester_test.py",
            additional_opts=["--sc-type", "test", "--sc-only", "--sc-target", percent],
            outcomes={"passed": 0},
        )

    with allure.step("Check summary for coverage percent"):
        # Last one line will be greetings while previous one with stats
        assert any(
            f"{percent}%" in outline for outline in pytester_result.outlines
        ), f'Should be "{percent}%" in outlines'
    with allure.step("Check tests without spec"):
        assert (
            "There are tests without spec: test_abandoned_case, test_non_existent_scenario_case, "
            "test_one_parameter_marked_only[1]"
        ) in pytester_result.outlines, "Should be message about tests without specs"


@pytest.mark.usefixtures("_conftest")
def test_sc_only(pytester: Pytester):
    """Test --sc-only and --sc-target options"""

    with allure.step("Assert that --sc-only not running tests"):
        pytester_result, _ = run_with_allure(
            pytester=pytester,
            testfile_path="sc_only_test.py",
            additional_opts=["--sc-type", "test", "--sc-only"],
            outcomes={"passed": 0},
        )
        assert pytester_result.ret == ExitCode.NO_TESTS_COLLECTED
        assert any(
            "_pytest.outcomes.Exit" in outline for outline in pytester_result.outlines
        ), 'Should be "_pytest.outcomes.Exit" in outlines'
        assert any(
            "50% specification coverage" in outline for outline in pytester_result.outlines
        ), 'Should be "50% specification coverage" in outlines'
    with allure.step("Assert that --sc-target less than coverage"):
        pytester_result, _ = run_with_allure(
            pytester=pytester,
            testfile_path="sc_only_test.py",
            additional_opts=["--sc-type", "test", "--sc-only", "--sc-target", "25"],
            outcomes={"passed": 0},
        )
        assert any("🎉🎉🎉" in outline for outline in pytester_result.outlines), 'Should be "🎉🎉🎉" in outlines'
