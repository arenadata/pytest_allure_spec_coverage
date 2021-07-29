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
"""Test that spec collectors is ok"""
# pylint: disable=redefined-outer-name,unused-argument
import os
from pathlib import Path
from typing import Mapping

import pytest
import toml
from pytest_allure_spec_coverage.config_provider import ConfigProvider
from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Parent, Scenario
from pytest_allure_spec_coverage.spec_collectors import SphinxCollector

SCENARIOS = [
    Scenario(
        name="simple_scenario",
        display_name="Simple scenario",
        parents=[Parent(name="scenarios", display_name="There is some scenarios")],
        link=None,
        branch=None,
    ),
    Scenario(
        name="scenario_with_parent",
        display_name="Scenario with parent",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
            Parent(name="parent_folder", display_name="Parent folder for scenarios"),
        ],
        link=None,
        branch=None,
    ),
    Scenario(
        name="scenario_with_parents",
        display_name="Scenario with two level of parents",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
            Parent(name="parent_folder", display_name="Parent folder for scenarios"),
            Parent(name="second_level_parent", display_name="Second level parent folder"),
        ],
        link=None,
        branch=None,
    ),
]


class TestCollector(Collector):
    """Simple collector for config test"""

    def collect(self):
        """Nothing to do"""

    def setup_config(self):
        """Nothing to do"""


@pytest.fixture()
def pyproject_toml(request):
    """pyproject content"""
    if not hasattr(request, "param"):
        raise ValueError("Please parametrize fixture by pyproject config value")
    return {"tool": {"pytest_allure_spec_coverage": request.param}}


@pytest.fixture()
def collector_config_path(pyproject_toml: Mapping, tmpdir):
    """Returns path to pyproject config file"""
    config_path = os.path.join(tmpdir, "pyproject.toml")
    with open(config_path, "w") as config_file:
        toml.dump(pyproject_toml, config_file)
    return config_path


@pytest.fixture()
def config_provider(collector_config_path: str):
    """Config provider"""
    path = Path(collector_config_path).parent
    return ConfigProvider(path)


@pytest.fixture()
def test_collector(config_provider: ConfigProvider):
    """Simple test collector"""
    return TestCollector(config=config_provider.config)


@pytest.fixture()
def sphinx_collector(config_provider: ConfigProvider):
    """Prepared sphinx collector"""
    return SphinxCollector(config=config_provider.config)


@pytest.mark.parametrize("pyproject_toml", [{"option": "value"}], ids=["simple_config"], indirect=True)
def test_config_provider_loading(config_provider: ConfigProvider):
    """Test that pyproject.toml load successful"""
    assert config_provider.config.get("option") == "value", "Option from config not found"


@pytest.mark.parametrize(
    "pyproject_toml", [{"sphinx_dir": "tests/sphinx_spec/scenarios"}], ids=["simple_scenarios"], indirect=True
)
def test_sphinx_collector(sphinx_collector):
    """Test that sphinx scenarios collected"""
    scenarios = sphinx_collector.collect()
    assert scenarios == SCENARIOS, "Collected scenarios doesn't equal expected"


@pytest.mark.parametrize(
    "pyproject_toml",
    [
        {"sphinx_dir": "tests/sphinx_spec/scenarios", "spec_endpoint": "https://spec.url"},
    ],
    ids=["with_endpoint"],
    indirect=True,
)
def test_sphinx_collector_with_endpoint(sphinx_collector):
    """
    Test that sphinx scenarios has link
    """
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link, "Scenario link should exists"
        assert scenario.link == f"https://spec.url/{scenario.id}.html"


@pytest.mark.parametrize(
    "pyproject_toml",
    [
        {"sphinx_dir": "tests/sphinx_spec/scenarios", "spec_endpoint": "https://spec.url"},
    ],
    ids=["with_endpoint_and_branch"],
    indirect=True,
)
def test_sphinx_collector_with_endpoint_and_branch(sphinx_collector):
    """
    Test that sphinx scenarios has link
    """
    os.environ["BRANCH"] = "master"
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link, "Scenario link should exists"
        assert scenario.link == f"https://spec.url/{scenario.id}.html"

    os.environ["BRANCH"] = "feature"
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link, "Scenario link should exists"
        parents = "/".join([parent.name for parent in scenario.parents])
        assert scenario.link == f"https://spec.url/feature/{parents}/{scenario.name}.html"
