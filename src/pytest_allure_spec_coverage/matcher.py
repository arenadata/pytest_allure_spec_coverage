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
import itertools
import os
import warnings
from dataclasses import dataclass, field
from typing import (
    Callable,
    ClassVar,
    Collection,
    Iterable,
    List,
    Mapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
)
import pytest
from _pytest.config import ExitCode
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.terminal import TerminalReporter
from allure_commons.model2 import Label, Link, Status, StatusDetails, TestResult
from allure_commons.reporter import AllureReporter
from allure_commons.types import LabelType, LinkType
from allure_commons.utils import uuid4
from allure_pytest.utils import ALLURE_LABEL_MARK, ALLURE_LINK_MARK

from .config_provider import ConfigProvider
from .models.collector import Collector
from .models.scenario import Scenario
from .xdist_shared import XdistSharedStorage


class SpecCollectorWarning(UserWarning):
    """Warn for spec collector issues"""


def is_xdist_first_worker():
    """True if running on first xdist worker"""
    return os.getenv("PYTEST_XDIST_WORKER") == "gw0"


def is_xdist_root():
    """True if xdist master or xdist not used"""
    return os.getenv("PYTEST_XDIST_WORKER", "root") == "root"


def scenario_ids(item: Item) -> Iterable[str]:
    """Get scenario identifiers from pytest.Item"""

    return itertools.chain.from_iterable(mark.args for mark in item.iter_markers(ScenariosMatcher.MARKER_NAME))


def shrink_values_by_length(values: MutableSequence[str], expected_length: int):
    """Shrink collection to the given length.

    >>> list_ = ["a", "b", "c"]
    >>> shrink_values_by_length(list_, 2)
    >>> list_
    ['a', 'b.c']
    >>> shrink_values_by_length(list_, 2)
    >>> list_
    ['a', 'b.c']
    >>> shrink_values_by_length(list_, 3)
    >>> list_
    ['a', 'b.c']
    >>> shrink_values_by_length(list_, 0)
    >>> list_
    []
    """

    if not expected_length:
        values[:] = []

    if len(values) > expected_length:
        itv = slice(expected_length - 1, None)
        values[itv] = [".".join(values[itv])]


def make_allure_labels(names: Sequence[str], values: Sequence[str]) -> Iterable[Label]:
    """Generate Allure labels by the given names and values.

    >>> list(make_allure_labels(("a", "b", "c"), ("p", "y", "3")))
    [Label(name='a', value='p'), Label(name='b', value='y'), Label(name='c', value='3')]
    >>> list(make_allure_labels(("a", "b", "c"), ("h", "e", "l", "l", "c")))
    [Label(name='a', value='h'), Label(name='b', value='e'), Label(name='c', value='l.l.c')]
    """

    values_copy = list(values)
    shrink_values_by_length(values_copy, len(names))
    for name, value in zip(names, values_copy):
        yield Label(name, value)


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
    build_summary_stats_line: Callable,
    spec_coverage_percent: int,
) -> Callable:
    """
    This function needs to be called by default pytest TerminalReporter
    for specification coverage percent in the summary stats line
    """

    def _wrapped():
        main_parts, main_color = build_summary_stats_line()
        report_color = _select_report_color(spec_coverage_percent)
        main_parts.append((f"{spec_coverage_percent}% specification coverage", {report_color: True}))
        return main_parts, main_color

    return _wrapped


@dataclass
class PytestItems:
    """All pytest items collection - selected and deselected"""

    selected: List[pytest.Item] = field(default_factory=list)
    deselected: List[pytest.Item] = field(default_factory=list)


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

    config: ConfigProvider
    collector: Type[Collector]
    reporter: AllureReporter
    storage: Optional[XdistSharedStorage]

    scenarios: Collection[Scenario] = field(default_factory=list)
    nonexistent: [PytestItems] = field(default_factory=list)
    matches: Mapping[Scenario, PytestItems] = field(default_factory=dict)

    @property
    def missed(self) -> Iterable[Scenario]:
        """Not implemented scenarios"""

        return (
            scenario
            for scenario, pytest_items in self.matches.items()
            if not pytest_items.selected and not pytest_items.deselected
        )

    @property
    def deselected(self) -> Iterable[Scenario]:
        """Deselected scenarios"""

        return (
            scenario
            for scenario, pytest_items in self.matches.items()
            if not pytest_items.selected and pytest_items.deselected
        )

    @property
    def spec_coverage_percent(self):
        """Coverage percent"""
        return int((len(self.scenarios) - len(tuple(self.missed))) / len(self.scenarios) * 100)

    def match(self, items: List[pytest.Item], deselected: bool = False) -> None:
        """Match collected tests items with its scenarios"""

        if not self.matches:
            self.matches = {sc: PytestItems() for sc in self.scenarios}
        sc_lookup = {sc.id: sc for sc in self.scenarios}
        for item in items:
            for key in scenario_ids(item):
                if key not in sc_lookup:
                    self.nonexistent.append(item)
                else:
                    if deselected:
                        self.matches[sc_lookup[key]].deselected.append(item)
                    else:
                        self.matches[sc_lookup[key]].selected.append(item)

    def mark(self) -> None:
        """Add markers with links to spec for matched items"""

        for scenario, pytest_items in self.matches.items():
            for item in pytest_items.selected:
                self._add_link(scenario, item)
                self._add_labels(scenario, item)

    def _add_link(self, scenario: Scenario, item: Item) -> None:
        if not scenario.link:
            return

        link_marker = getattr(pytest.mark, ALLURE_LINK_MARK)
        item.add_marker(
            link_marker(
                scenario.link,
                name=self.config.get("link_label"),
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
            self._report_missed_scenario(scenario)
        for scenario in self.deselected:
            self._report_deselected_scenario(scenario)

    def _report_missed_scenario(self, scenario: Scenario):
        self._report_scenario(scenario)

    def _report_deselected_scenario(self, scenario: Scenario):
        details = StatusDetails(
            message="Scenario was covered but tests for this scenario were deselected",
            trace="Deselected tests covering this scenario:\n"
            + "\n".join(item.nodeid for item in self.matches[scenario].deselected),
        )
        self._report_scenario(scenario, status=Status.SKIPPED, status_details=details)

    def _report_scenario(self, scenario: Scenario, status=Status.UNKNOWN, status_details=None) -> None:
        fake_uuid = uuid4()
        fake_result = TestResult(
            uuid=fake_uuid,
            name=scenario.display_name,
            status=status,
            statusDetails=status_details,
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
                name=self.config.get("link_label"),
                type=LinkType.LINK,
            )
        ]

    def _labels(self, scenario: Scenario, keep_default: bool = True) -> Collection[Label]:
        """Make labels for Allure from the given scenario"""

        custom_labels = self.config.get("allure_labels")
        default_labels = self.DEFAULT_LABELS if keep_default else []

        return (
            *make_allure_labels(default_labels, scenario.suites_names),
            *make_allure_labels(custom_labels, scenario.specifications_names),
        )

    def pytest_sessionstart(self):
        """Collect scenarios on session start"""

        self.scenarios = self.collector(config=self.config).collect()

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session: Session, items: List[pytest.Item]) -> None:
        """Collect implemented test cases after items collection complete"""
        self.match(items)
        if not self.reporter:
            return

        self.mark()
        if self.storage and not is_xdist_first_worker() and not is_xdist_root():
            return
        self.report()
        if self.storage and is_xdist_first_worker():
            self.storage.write(session.config, "spec_coverage_percent", self.spec_coverage_percent)

    @pytest.hookimpl(tryfirst=True)
    def pytest_deselected(self, items: List[pytest.Item]):
        """Collect deselected tests cases"""
        self.match(items, deselected=True)

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_collection_finish(self):
        """
        This hook exit pytest if need to check coverage percent
        Important that fail will be after terminal reporting hooks
        """
        yield
        warn_message = ""
        if self.nonexistent:
            tests_without_spec = "\n    ".join(item.name for item in self.nonexistent)
            warn_message = f"The following tests linked with nonexistent spec:\n    {tests_without_spec}"
        if not self.config.fail_under:
            if warn_message:
                warnings.warn(SpecCollectorWarning(warn_message))
        else:
            exit_message = ""
            if self.spec_coverage_percent < self.config.fail_under:
                exit_message += (
                    f"Spec coverage percent is {self.spec_coverage_percent}%, "
                    f"and it is less than target {self.config.fail_under}%\n"
                )
            if exit_message or warn_message:
                pytest.exit(
                    exit_message + warn_message,
                    returncode=ExitCode.NO_TESTS_COLLECTED,
                )

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        """
        Add specification coverage percent to summary stats line
        """
        if not is_xdist_root():
            return
        if self.storage and self.storage.is_xdist_master(terminalreporter.config):
            percent = int(self.storage.get(terminalreporter.config, "spec_coverage_percent"))
        else:
            percent = self.spec_coverage_percent
        terminalreporter.build_summary_stats_line = _build_summary_stats_line(
            terminalreporter.build_summary_stats_line, percent
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """After terminal summary we print spec coverage success message"""
        yield
        if self.config.fail_under and exitstatus != ExitCode.NO_TESTS_COLLECTED:
            terminal = session.config.pluginmanager.get_plugin("terminalreporter")
            terminal.write_line(f"Spec coverage is greater than target {self.config.fail_under}%! 🎉🎉🎉")
