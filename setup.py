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
"""pytest_allure_spec_coverage setup settings"""

from setuptools import setup, find_packages

setup(
    name="pytest_allure_spec_coverage",
    description="The pytest plugin aimed to display test coverage of the specs(requirements) in Allure",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    version="0.0.2",
    # the following makes a plugin available to pytest
    entry_points={"pytest11": ["pytest_allure_spec_coverage = pytest_allure_spec_coverage.plugin"]},
    # custom PyPI classifier for pytest plugins
    install_requires=["pytest", "allure-pytest", "toml", "docutils", "pluggy"],
    classifiers=["Framework :: Pytest"],
)
