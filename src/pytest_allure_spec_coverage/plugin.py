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
from dataclasses import dataclass
from typing import Iterable, MutableMapping, Type

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.config.exceptions import UsageError
from pluggy import PluginManager

from .common import allure_listener
from .config_provider import ConfigProvider
from .matcher import ScenariosMatcher
from .models.collector import Collector
from .spec_collectors.sphinx import SphinxCollector
from .xdist_shared import XdistSharedStorage

CollectorsMapping = MutableMapping[str, Type[Collector]]


def pytest_addhooks(pluginmanager: PluginManager) -> None:
    """Register plugin hooks"""

    # pylint: disable=import-outside-toplevel
    from pytest_allure_spec_coverage import hooks

    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser: Parser) -> None:
    """Register plugin options"""
    group = parser.getgroup("Spec coverage plugin")
    group.addoption(
        "--sc-type", "--spec-coverage-type", action="store", type=str, help="Spec collector type string identifier"
    )
    group.addoption(
        "--sc-only",
        "--spec-coverage-only",
        action="store_true",
        help="Calculate spec coverage and exit without test running. "
        "If the spec coverage percent less than target value, then exit with a status code of 2",
    )
    group.addoption(
        "--sc-target",
        "--spec-coverage-target",
        action="store",
        type=int,
        default=100,
        help="The target of spec coverage percent. Used together with --spec-coverage-only",
    )
    parser.addini(
        "allure_labels", "What labels to use for spec tree. Example: epic, feature, story", type="linelist", default=[]
    )
    parser.addini("link_label", "What link label to be", type="string", default="Scenario")


def pytest_register_spec_collectors(collectors: CollectorsMapping) -> None:
    """Register available spec collectors"""

    collectors["sphinx"] = SphinxCollector


@dataclass(eq=False)
class CollectorsPlugin:
    """Simple plugin to register all collector options"""

    collectors: Iterable[Type[Collector]]

    def pytest_addoption(self, parser: Parser) -> None:
        """Register plugin options"""
        for collector in self.collectors:
            collector.addoption(parser)


@pytest.hookimpl(trylast=True)
def pytest_configure(config: Config) -> None:
    """Validate preconditions and register required components"""

    listener = allure_listener(config)
    collectors: CollectorsMapping = {}
    config.hook.pytest_register_spec_collectors(collectors=collectors)
    config.pluginmanager.register(CollectorsPlugin(collectors=collectors.values()))
    config.addinivalue_line("markers", f"{ScenariosMatcher.MARKER_NAME}(link): test function scenario link")
    if config.pluginmanager.hasplugin("xdist"):
        storage = XdistSharedStorage()
        config.pluginmanager.register(storage)
    else:
        storage = None

    if not config.option.sc_type:
        return

    if config.option.sc_type not in collectors.keys():
        raise UsageError(f"Unexpected collector type, registered ones: {collectors.keys()}")
    if config.option.sc_only:
        config.option.collectonly = True
    cfg_provider = ConfigProvider(pytest_config=config)
    sc_type = collectors[config.option.sc_type]
    reporter = None if not listener else listener.allure_logger
    matcher = ScenariosMatcher(config=cfg_provider, reporter=reporter, collector=sc_type, storage=storage)
    config.pluginmanager.register(matcher, ScenariosMatcher.PLUGIN_NAME)
