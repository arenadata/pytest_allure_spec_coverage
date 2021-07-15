import os.path
from unittest import mock

import pytest
import toml

from pytest_allure_spec_coverage.models.Collector import Collector
from pytest_allure_spec_coverage.models.Scenario import Scenario, Parent
from pytest_allure_spec_coverage.spec_collectors import SphinxCollector

SCENARIOS = [
    Scenario(
        name='simple_scenario',
        display_name='Simple scenario',
        parents=[
            Parent(name='scenarios', display_name='There is some scenarios')
        ],
        link=None,
        branch=None),
    Scenario(
        name='scenario_with_parent',
        display_name='Scenario with parent',
        parents=[
            Parent(name='scenarios', display_name='There is some scenarios'),
            Parent(name='parent_folder', display_name='Parent folder for scenarios')
        ],
        link=None,
        branch=None),
    Scenario(
        name='scenario_with_parents',
        display_name='Scenario with two level of parents',
        parents=[
            Parent(name='scenarios', display_name='There is some scenarios'),
            Parent(name='parent_folder', display_name='Parent folder for scenarios'),
            Parent(name='second_level_parent', display_name='Second level parent folder')
        ],
        link=None,
        branch=None)
]


class TestCollector(Collector):

    def collect(self):
        pass

    def validate_config(self):
        pass


@pytest.fixture()
def pyproject_toml(request):
    return {"tool": {"pytest_allure_spec_coverage": request.param}}


@pytest.fixture()
def collector_config_path(pyproject_toml, tmpdir):
    config_path = os.path.join(tmpdir, "pyproject.toml")
    with open(config_path, "w") as config_file:
        toml.dump(pyproject_toml, config_file)
    return config_path


@pytest.fixture()
def test_collector(collector_config_path):
    TestCollector.path_to_config_file = mock.PropertyMock(return_value=collector_config_path)
    collector = TestCollector()
    return collector


@pytest.fixture()
def sphinx_collector(collector_config_path):
    SphinxCollector.path_to_config_file = mock.PropertyMock(return_value=collector_config_path)
    collector = SphinxCollector()
    return collector


@pytest.mark.parametrize("pyproject_toml", [
    {"option": "value"}
], ids=["simple_config"], indirect=True)
def test_collector_config_loading(pyproject_toml, test_collector):
    assert test_collector.config.get("option") == "value", "Option from config not found"


@pytest.mark.parametrize("pyproject_toml", [
    {"sphinx_dir": "tests/sphinx_spec/scenarios"}
], ids=["simple_scenarios"], indirect=True)
def test_sphinx_collector(pyproject_toml, sphinx_collector):
    scenarios = sphinx_collector.collect()
    assert scenarios == SCENARIOS


@pytest.mark.parametrize("pyproject_toml", [
    {"sphinx_dir": "tests/sphinx_spec/scenarios", "spec_endpoint": "https://spec.url"},
], ids=["with_endpoint"], indirect=True)
def test_sphinx_collector_with_endpoint(pyproject_toml, sphinx_collector):
    scenarios = sphinx_collector.collect()
    for scenario in scenarios:
        assert scenario.link
        assert scenario.link.startswith("https://spec.url")
