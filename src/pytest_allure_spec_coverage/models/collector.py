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
import os
from abc import ABC, abstractmethod
from typing import Optional, List

import toml

from pytest_allure_spec_coverage.models.scenario import Scenario


class Collector(ABC):
    """
    Abstract collector
    """

    config: Optional[dict] = None
    path_to_config_file = "pyproject.toml"

    def __init__(self):
        self.read_config()

    @abstractmethod
    def collect(self) -> List[Scenario]:
        """
        Main method of collect scenarios
        """

    @abstractmethod
    def validate_config(self):
        """
        Collector by default read configuration without validation
        Each collector needs its own config params
        """

    def read_config(self):
        """Read pyproject.yaml and save plugin config"""
        if os.path.exists(self.path_to_config_file):
            config = toml.load(self.path_to_config_file)
            self.config = config.get("tool", {}).get("pytest_allure_spec_coverage", {})
            self.validate_config()
