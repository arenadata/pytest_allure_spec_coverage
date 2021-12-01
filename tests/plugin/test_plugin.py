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
"""
Test common plugin behaviour
"""
from _pytest.pytester import Pytester

from tests.plugin.common import run_with_allure


def test_skip_if_testplan_exists(pytester: Pytester, monkeypatch):
    """
    Test that plugin is disabled if allure testplan exists
    """
    monkeypatch.setenv("ALLURE_TESTPLAN_PATH", "testplan.json")
    opts = ["--sc-type", "something"]
    pytester_result, _ = run_with_allure(pytester=pytester, testfile_path="simple_test.py", additional_opts=opts)
    assert "Spec coverage plugin is disabled due to allure testplan exists" in pytester_result.outlines
