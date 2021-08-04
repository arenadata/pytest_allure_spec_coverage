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
from dataclasses import dataclass
from functools import cached_property
from _pytest.config import Config


@dataclass
class ConfigProvider:
    """Provides config for the plugin from pytest config object"""

    pytest_config: Config

    def get(self, name: str):
        """Get option by name"""
        return self.pytest_config.getini(name)

    @cached_property
    def root(self):
        """Get config root path"""
        return self.pytest_config.rootpath
