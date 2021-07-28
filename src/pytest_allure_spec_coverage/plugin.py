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

"""Main plugin module"""

from contextlib import suppress
from dataclasses import dataclass, field
from typing import ClassVar, Collection, Iterable, List, Mapping, MutableMapping, Optional, Type

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.config.exceptions import UsageError
from _pytest.mark.structures import Mark
from _pytest.nodes import Item
from allure_commons.model2 import Label, Link, Status, TestResult
from allure_commons.reporter import AllureReporter
from allure_commons.types import LinkType
from allure_commons.utils import uuid4
from allure_pytest.listener import AllureListener
from allure_pytest.utils import ALLURE_LINK_MARK
from pluggy.manager import PluginManager

from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Scenario
from pytest_allure_spec_coverage.spec_collectors.sphinx import SphinxCollector

CollectorsMapping = MutableMapping[str, Type[Collector]]


def safe_get_marker(item: Item, name: str) -> Mark:
    """Safely get pytest.Item marker"""

    stub_marker = Mark(name="stub", args=(), kwargs={})
    return item.get_closest_marker(name, stub_marker)


def scenario_ids(item: Item) -> Iterable[str]:
    """Get scenario identifiers from pytest.Item"""

    return safe_get_marker(item, ScenariosMatcher.MARKER_NAME).args


def allure_labels(scenario: Scenario) -> List[Label]:
    """Make labels for Allure from the given scenario"""

    labels = ("parentSuite", "suite", "subSuite")
    values = [p.display_name for p in scenario.parents]
    if len(values) > 3:
        itv = slice(2, None)
        values[itv] = [".".join(values[itv])]
    return [Label(label, value) for label, value in zip(labels, values)]


def allure_links(scenario: Scenario) -> List[Link]:
    """Make links for Allure from the given scenario"""

    return [Link(url=scenario.link, name="Scenario", type=LinkType.LINK)]


@dataclass(eq=False)
class ScenariosMatcher:
    """Match collected test cases with collected scenarios and report missed ones"""

    PLUGIN_NAME: ClassVar[str] = "smatcher"
    MARKER_NAME: ClassVar[str] = "scenario"

    config: Config
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

        link_marker = getattr(pytest.mark, ALLURE_LINK_MARK)
        for scenario, items in self.matches.items():
            for item in items:
                item.add_marker(
                    link_marker(
                        scenario.link,
                        name="Scenario",
                        link_type=LinkType.LINK,
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
            name=scenario.name,
            description=scenario.display_name,
            status=Status.UNKNOWN,
            labels=allure_labels(scenario),
            links=allure_links(scenario),
        )
        self.reporter.schedule_test(uuid=fake_uuid, test_case=fake_result)
        self.reporter.close_test(uuid=fake_uuid)

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

    def pytest_sessionfinish(self) -> None:
        """Add entries to report after session complete"""

        self.report()


def pytest_addhooks(pluginmanager: PluginManager) -> None:
    """Register plugin hooks"""

    # pylint: disable=import-outside-toplevel
    from pytest_allure_spec_coverage import hooks

    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser: Parser) -> None:
    """Register plugin options"""

    parser.addoption("--sc-type", action="store", type=str, help="Spec collector type string identifier")
    parser.addoption("--sc-cfgpath", action="store", type=str, help="Path to spec collector configuration file")


def pytest_register_spec_collectors(collectors: CollectorsMapping) -> None:
    """Register available spec collectors"""

    collectors["sphinx"] = SphinxCollector


@pytest.hookimpl(trylast=True)
def pytest_configure(config: Config) -> None:
    """Validate preconditions and register required components"""

    listener: Optional[AllureListener] = next(
        filter(
            lambda plugin: (isinstance(plugin, AllureListener)),
            dict(config.pluginmanager.list_name_plugin()).values(),
        ),
        None,
    )

    if not listener or not config.option.sc_type:
        return

    collectors: CollectorsMapping = {}
    config.hook.pytest_register_spec_collectors(collectors=collectors)
    if config.option.sc_type not in collectors.keys():
        raise UsageError(f"Unexpected collector type, registered ones: {collectors.keys()}")
    sc_type = collectors[config.option.sc_type]
    sc_type.path_to_config_file = config.option.sc_cfgpath or sc_type.path_to_config_file
    collector: Collector = sc_type()

    matcher = ScenariosMatcher(config=config, reporter=listener.allure_logger, collector=collector)
    config.pluginmanager.register(matcher, ScenariosMatcher.PLUGIN_NAME)
