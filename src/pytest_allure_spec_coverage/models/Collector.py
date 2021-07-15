import os
from abc import ABC, abstractmethod
from typing import Optional, List

import toml

from pytest_allure_spec_coverage.models.Scenario import Scenario


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
        pass

    @abstractmethod
    def validate_config(self):
        """
        Collector by default read configuration without validation
        Each collector needs its own config params
        """
        pass

    def read_config(self):
        if os.path.exists(self.path_to_config_file):
            config = toml.load(self.path_to_config_file)
            self.config = config.get("tool", {}).get("pytest_allure_spec_coverage", {})
            self.validate_config()
