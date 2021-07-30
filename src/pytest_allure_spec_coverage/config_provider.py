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

"""Plugin config provider"""
import warnings
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import ClassVar, Mapping, Optional

import toml


@dataclass
class ConfigProvider:
    """Provides config for the plugin via parsing pyproject.toml file"""

    TOOL_KEY: ClassVar[str] = "pytest_allure_spec_coverage"
    FILENAME: ClassVar[str] = "pyproject.toml"

    path_to_config_file: Path

    @cached_property
    def config(self) -> Optional[Mapping]:
        """Read all params related to pytest_allure_spec_coverage from pyproject.toml"""

        try:
            config = toml.load(self.path_to_config_file / self.FILENAME)
            return config.get("tool", {}).get(self.TOOL_KEY, {})
        except FileNotFoundError:
            warnings.warn(f"Unable to load configuration file {self.path_to_config_file / self.FILENAME}")
            return None
