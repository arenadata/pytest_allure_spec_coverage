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
"""Abstract collector"""

from abc import ABC, abstractmethod
from typing import List

from _pytest.config.argparsing import Parser

from pytest_allure_spec_coverage.config_provider import ConfigProvider
from pytest_allure_spec_coverage.models.scenario import Scenario


class Collector(ABC):
    """
    Abstract collector
    """

    def __init__(self, config: ConfigProvider):
        self.config = config
        self.setup_config()

    @abstractmethod
    def collect(self) -> List[Scenario]:
        """
        The main method of collect scenarios. Should return a flat list of Scenario objects
        """

    @abstractmethod
    def setup_config(self):
        """
        Each collector can have an individual config structure.
        This method will be called at the final stage of the config load
        to validate its structure and assigment config variables

        Raises:
            ValueError: if config validation fails
        """

    @staticmethod
    @abstractmethod
    def addoption(parser: Parser):
        """Implementation of pytest_addoption hook"""
