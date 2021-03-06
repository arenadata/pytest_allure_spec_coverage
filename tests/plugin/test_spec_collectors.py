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
from dataclasses import dataclass
from pathlib import Path

import pytest

from pytest_allure_spec_coverage.config_provider import ConfigProvider
from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Parent, Scenario
from pytest_allure_spec_coverage.spec_collectors import SphinxCollector

CURR_DIR = Path(__file__).parent
SPEC_DIR = str(CURR_DIR / ".." / "examples" / "sphinx_spec" / "scenarios")

SCENARIOS = [
    Scenario(
        id="simple_scenario",
        name="simple_scenario",
        display_name="Simple scenario",
        parents=[Parent(name="scenarios", display_name="There is some scenarios")],
    ),
    Scenario(
        id="deselected_scenario",
        name="deselected_scenario",
        display_name="Deselected scenario",
        parents=[Parent(name="scenarios", display_name="There is some scenarios")],
    ),
    Scenario(
        id="parent_folder/scenario_with_parent",
        name="scenario_with_parent",
        display_name="Scenario with parent",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
            Parent(name="parent_folder", display_name="Parent folder for scenarios"),
        ],
    ),
    Scenario(
        id="parent_folder/second_level_parent/scenario_with_parents",
        name="scenario_with_parents",
        display_name="Scenario with two level of parents",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
            Parent(name="parent_folder", display_name="Parent folder for scenarios"),
            Parent(name="second_level_parent", display_name="Second level parent folder"),
        ],
    ),
]


class TestCollector(Collector):
    """Simple collector for config test"""

    def collect(self):
        """Nothing to do"""

    def setup_config(self):
        """Nothing to do"""

    @staticmethod
    def addoption(parser):
        """Nothing to do"""


@dataclass
class TestConfigProvider(ConfigProvider):
    """Test config provider for support config parametrization"""

    test_config: dict
    pytest_config: dict

    def get(self, name: str):
        return self.test_config.get(name) or super().get(name)


@pytest.fixture()
def config_provider(request):
    """Config provider"""
    return TestConfigProvider(test_config=getattr(request, "param", {}), pytest_config=request.config)


@pytest.fixture()
def test_collector(config_provider: ConfigProvider):
    """Simple test collector"""
    return TestCollector(config=config_provider)


@pytest.fixture()
def sphinx_collector(config_provider: ConfigProvider):
    """Prepared sphinx collector"""
    return SphinxCollector(config=config_provider)


@pytest.mark.parametrize("config_provider", [{"sphinx_dir": SPEC_DIR}], ids=["simple_scenarios"], indirect=True)
def test_sphinx_collector(sphinx_collector, monkeypatch):
    """Test that sphinx scenarios collected"""
    monkeypatch.delenv("BRANCH_NAME", raising=False)
    scenarios = sphinx_collector.collect()
    assert scenarios == SCENARIOS, "Collected scenarios doesn't equal expected"


@pytest.mark.parametrize(
    "config_provider",
    [{"sphinx_dir": SPEC_DIR, "spec_endpoint": "https://spec.url"}],
    ids=["with_endpoint"],
    indirect=True,
)
def test_sphinx_collector_with_endpoint(sphinx_collector, monkeypatch):
    """
    Test that sphinx scenarios has link
    """
    monkeypatch.delenv("BRANCH_NAME", raising=False)
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link, "Scenario link should exists"
        assert scenario.link == f"https://spec.url/{scenario.parents[0].name}/{scenario.id}.html"


@pytest.mark.parametrize(
    "config_provider",
    [{"sphinx_dir": SPEC_DIR, "spec_endpoint": "https://spec.url"}],
    ids=["with_endpoint_and_branch"],
    indirect=True,
)
def test_sphinx_collector_with_endpoint_and_branch(sphinx_collector, monkeypatch):
    """
    Test that sphinx scenarios has link
    """
    monkeypatch.setenv("BRANCH_NAME", "master")
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link, "Scenario link should exists"
        assert scenario.link == f"https://spec.url/{scenario.parents[0].name}/{scenario.id}.html"

    monkeypatch.setenv("BRANCH_NAME", "feature/ISSUE-123")
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link, "Scenario link should exists"
        parents = "/".join([parent.name for parent in scenario.parents])
        assert scenario.link == f"https://spec.url/feature_ISSUE-123/{parents}/{scenario.name}.html"
