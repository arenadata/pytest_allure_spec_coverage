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

"""Matcher of tests cases and scenarios"""
from contextlib import suppress
from dataclasses import dataclass, field
from typing import ClassVar, Collection, Iterable, List, Mapping, Optional, Tuple, Callable, Dict

import pytest
from _pytest.config import Config
from _pytest.mark.structures import Mark
from _pytest.nodes import Item
from _pytest.terminal import TerminalReporter
from allure_commons.model2 import Label, Link, Status, TestResult
from allure_commons.reporter import AllureReporter
from allure_commons.types import LabelType, LinkType
from allure_commons.utils import uuid4
from allure_pytest.utils import ALLURE_LABEL_MARK, ALLURE_LINK_MARK

from .models.collector import Collector
from .models.scenario import Scenario


def safe_get_marker(item: Item, name: str) -> Mark:
    """Safely get pytest.Item marker"""

    stub_marker = Mark(name="stub", args=(), kwargs={})
    return item.get_closest_marker(name, stub_marker)


def scenario_ids(item: Item) -> Iterable[str]:
    """Get scenario identifiers from pytest.Item"""

    return safe_get_marker(item, ScenariosMatcher.MARKER_NAME).args


def _select_report_color(spec_coverage_percent: int):
    """
    >>> _select_report_color(0)
    'red'
    >>> _select_report_color(50)
    'red'
    >>> _select_report_color(84)
    'red'
    >>> _select_report_color(85)
    'yellow'
    >>> _select_report_color(90)
    'yellow'
    >>> _select_report_color(99)
    'yellow'
    >>> _select_report_color(100)
    'green'
    >>> _select_report_color(101) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: Invalid value: coverage_percent=101
    >>> _select_report_color(-1) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: Invalid value: coverage_percent=-1
    """
    percents_colors = {
        84: "red",
        99: "yellow",
        100: "green",
    }
    if spec_coverage_percent >= 0:
        for percent, color in percents_colors.items():
            if spec_coverage_percent <= percent:
                return color
    raise ValueError(f"Invalid value: {spec_coverage_percent=}")


def _build_summary_stats_line(
    spec_coverage_percent: int, main_parts: List[Tuple[str, Dict[str, bool]]], main_color: str
) -> Callable:
    """
    This function needs to be called by default pytest TerminalReporter
    for specification coverage percent in the summary stats line
    """

    def _wrapped():
        report_color = _select_report_color(spec_coverage_percent)
        main_parts.append((f"{spec_coverage_percent}% specification coverage", {report_color: True}))
        return main_parts, main_color

    return _wrapped


@dataclass(eq=False)
class ScenariosMatcher:
    """Match collected test cases with collected scenarios and report missed ones"""

    PLUGIN_NAME: ClassVar[str] = "smatcher"
    MARKER_NAME: ClassVar[str] = "scenario"

    DEFAULT_LABELS: ClassVar[Tuple[str, ...]] = (
        LabelType.PARENT_SUITE,
        LabelType.SUITE,
        LabelType.SUB_SUITE,
    )

    config: Mapping
    collector: Collector
    reporter: AllureReporter

    scenarios: Collection[Scenario] = field(default_factory=list)
    matches: Mapping[Scenario, List[pytest.Item]] = field(default_factory=dict)

    @property
    def missed(self) -> Iterable[Scenario]:
        """Not implemented scenarios"""

        return (scenario for scenario, items in self.matches.items() if not items)

    def match(self, items: List[pytest.Item]) -> None:
        """Match collected tests items with its scenarios"""

        self.matches = {sc: [] for sc in self.scenarios}
        sc_lookup = {sc.id: sc for sc in self.scenarios}
        for item in items:
            for key in scenario_ids(item):
                with suppress(KeyError):
                    self.matches[sc_lookup[key]].append(item)

    def mark(self) -> None:
        """Add markers with links to spec for matched items"""

        for scenario, items in self.matches.items():
            for item in items:
                self._add_link(scenario, item)
                self._add_labels(scenario, item)

    def _add_link(self, scenario: Scenario, item: Item) -> None:
        if not scenario.link:
            return

        link_marker = getattr(pytest.mark, ALLURE_LINK_MARK)
        item.add_marker(
            link_marker(
                scenario.link,
                name=self.config.get("link_label", "Scenario"),
                link_type=LinkType.LINK,
            )
        )

    def _add_labels(self, scenario: Scenario, item: Item) -> None:
        label_marker = getattr(pytest.mark, ALLURE_LABEL_MARK)
        for label in self._labels(scenario, keep_default=False):
            item.add_marker(
                label_marker(
                    label.value,
                    label_type=label.name,
                )
            )

    def report(self) -> None:
        """Report about not implemented scenarios"""

        for scenario in self.missed:
            self._report_scenario(scenario)

    def _report_scenario(self, scenario: Scenario) -> None:
        fake_uuid = uuid4()
        fake_result = TestResult(
            uuid=fake_uuid,
            name=scenario.display_name,
            status=Status.UNKNOWN,
            labels=self._labels(scenario),
            links=self._links(scenario),
        )
        self.reporter.schedule_test(uuid=fake_uuid, test_case=fake_result)
        self.reporter.close_test(uuid=fake_uuid)

    def _links(self, scenario: Scenario) -> Optional[List[Link]]:
        """Make links for Allure from the given scenario"""

        if not scenario.link:
            return None

        return [
            Link(
                url=scenario.link,
                name=self.config.get("link_label", "Scenario"),
                type=LinkType.LINK,
            )
        ]

    def _labels(self, scenario: Scenario, keep_default: bool = True) -> Collection[Label]:
        """Make labels for Allure from the given scenario"""

        def shrink_values_by_length(values, expected_length):
            if len(values) > expected_length:
                itv = slice(expected_length - 1, None)
                values[itv] = [".".join(values[itv])]

        custom_labels = self.config.get("allure_labels", [])
        default_labels = self.DEFAULT_LABELS if keep_default else []

        spec_values = [p.display_name for p in scenario.parents[1:]] + [scenario.display_name]
        shrink_values_by_length(spec_values, len(custom_labels))

        suite_values = [p.display_name for p in scenario.parents]
        shrink_values_by_length(suite_values, len(default_labels))

        labels = []
        for label, value in zip(custom_labels, spec_values):
            labels.append(Label(label, value))

        for label, value in zip(default_labels, suite_values):
            labels.append(Label(label, value))

        return labels

    def pytest_configure(self, config: Config):
        """Add custom markers"""

        config.addinivalue_line("markers", f"{self.MARKER_NAME}(link): test function scenario link")

    def pytest_sessionstart(self):
        """Collect scenarios on session start"""

        self.scenarios = self.collector.collect()

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items: List[pytest.Item]) -> None:
        """Collect implemented test cases after items collection complete"""

        self.match(items)
        self.mark()

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Add entries to report after session complete"""
        try:
            import xdist  # pylint: disable=import-outside-toplevel
        except ImportError:
            pass
        else:
            if xdist.get_xdist_worker_id(session) not in ["master", "gw0"]:
                return
        self.report()

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        """
        Add specification coverage percent to summary stats line
        """
        spec_coverage_percent = int((len(self.scenarios) - len(tuple(self.missed))) / len(self.scenarios) * 100)

        main_parts, main_color = terminalreporter.build_summary_stats_line()
        terminalreporter.build_summary_stats_line = _build_summary_stats_line(
            spec_coverage_percent, main_parts, main_color
        )
