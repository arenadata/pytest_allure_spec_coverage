"""
Examples of scenarios and simple collector
"""
from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Scenario, Parent

scenarios = [
    Scenario(
        id="simple_scenario",
        name="simple_scenario",
        display_name="Simple scenario",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
        ],
        link="link://simple_scenario",
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
    ),
    Scenario(
        id="deselected_scenario",
        name="deselected_scenario",
        display_name="Deselected scenario",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
        ],
        link="link://deselected_scenario",
    ),
    Scenario(
        id="should_not_be_used",
        name="should_not_be_used",
        display_name="Should not be used",
        parents=[
            Parent(name="scenarios", display_name="There is some scenarios"),
        ],
        link="link://should_not_be_used",
    ),
]


class CollectorMock(Collector):
    """Collector mock class"""

    def collect(self):
        return scenarios

    def setup_config(self):
        """Does not required"""

    @staticmethod
    def addoption(parser):
        """Does not required"""
