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


from _pytest.config.argparsing import Parser, OptionGroup


# pylint: disable=redefined-outer-name
def pytest_addoption(parser: Parser):
    group: OptionGroup = parser.getgroup("Allure spec coverage",
                                         "Options related to pytest_allure_spec_coverage plugin")
    # TODO implement this
    group.addoption(
        "--spec_collector",
        action="store",
        default=None,
    )
