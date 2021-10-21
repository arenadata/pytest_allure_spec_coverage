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

"""Matcher test file to be run using pytester"""
# pylint: disable=unused-argument

import pytest


def test_abandoned_case():
    """Case without scenario mark"""


@pytest.mark.scenario("simple_scenario")
def test_single_scenario_case():
    """Case with the single one scenario"""


@pytest.mark.scenario("simple_scenario")
@pytest.mark.scenario("nested/scenario")
def test_multiple_scenarios_case():
    """Case with multiple implemented scenarios"""


@pytest.mark.scenario("simple_scenario")
@pytest.mark.scenario("simple_scenario")
def test_duplicated_scenarios_case():
    """Case marked by identical scenarios"""


@pytest.mark.scenario("deselected_scenario")
def test_deselected_scenario_case():
    """Case that will be deselected but covered scenario"""


@pytest.mark.parametrize("param", (1, 2))
@pytest.mark.scenario("simple_scenario")
def test_parametrized_case(param):
    """Case with parametrized argument"""


@pytest.mark.parametrize(
    "param",
    [
        1,
        pytest.param(2, marks=pytest.mark.scenario("simple_scenario")),
    ],
)
def test_one_parameter_marked_only(param):
    """Case with parametrized argument and mark applied to the single one param"""
