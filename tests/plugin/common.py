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

"""Common methods for plugin tests"""

import allure
from _pytest.pytester import Pytester, RunResult
from allure_commons_test.report import AllureReport


def run_tests(
    pytester: Pytester,
    testfile_path: str = None,
    makepyfile_str: str = None,
    *,
    additional_opts: list = None,
    outcomes=None,
) -> RunResult:
    """
    Run tests with pytest parameters from .py file or multiline string
    :param pytester: pytest.Pytester
    :param testfile_path: path to file to be copied to pytester directory
    :param makepyfile_str: multiline string for makepyfile method which will be running if param 'testfile_path' is None
    :param additional_opts: list of additional pytest launch parameters
    :param outcomes: optional outcomes expect. Ex. {"failed":1}
    """

    if testfile_path:
        pytester.copy_example(testfile_path)
    elif makepyfile_str:
        pytester.makepyfile(makepyfile_str)
    else:
        raise ValueError("At least one of the `testfile_path` or `makepyfile_str` should be passed.")

    additional_opts = additional_opts or []
    opts = ["-s", "-v", "--showlocals", *additional_opts]
    step_title = f"Run file {testfile_path}" if testfile_path else "Run test from multiline string"
    with allure.step(step_title):
        result = pytester.runpytest(*opts)
        allure.attach(
            "\n".join(result.outlines),
            name="Internal test console output",
            attachment_type=allure.attachment_type.TEXT,
        )
        outcomes = outcomes or dict(passed=1)
        result.assert_outcomes(**outcomes)
        return result


@allure.step("Run tests with mocked allure")
def run_with_allure(*args, **kwargs):
    """Run tests with fake allure logger"""

    addopts = kwargs.get("additional_opts", [])
    addopts.extend(["--alluredir", "allure-results"])
    kwargs["additional_opts"] = addopts
    result = run_tests(*args, **kwargs)
    allure_report = AllureReport("allure-results")
    return result, allure_report
