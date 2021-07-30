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

from pathlib import Path
from typing import MutableMapping, Optional, Type

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.config.exceptions import UsageError
from allure_pytest.listener import AllureListener
from pluggy.manager import PluginManager

from .config_provider import ConfigProvider
from .matcher import ScenariosMatcher
from .models.collector import Collector
from .spec_collectors.sphinx import SphinxCollector

CollectorsMapping = MutableMapping[str, Type[Collector]]


def pytest_addhooks(pluginmanager: PluginManager) -> None:
    """Register plugin hooks"""

    # pylint: disable=import-outside-toplevel
    from pytest_allure_spec_coverage import hooks

    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser: Parser) -> None:
    """Register plugin options"""

    parser.addoption("--sc-type", action="store", type=str, help="Spec collector type string identifier")
    parser.addoption(
        "--sc-cfgpath",
        action="store",
        type=Path,
        default=Path(),
        help="Path to spec collector configuration file",
    )


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
    cfg_provider = ConfigProvider(config.option.sc_cfgpath)
    if cfg_provider.config:
        collector: Collector = sc_type(config=cfg_provider.config)
        matcher = ScenariosMatcher(config=cfg_provider.config, reporter=listener.allure_logger, collector=collector)
        config.pluginmanager.register(matcher, ScenariosMatcher.PLUGIN_NAME)
