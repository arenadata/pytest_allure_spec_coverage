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
"""Models for scenario"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Parent:
    """Info about scenario parent (used for grouping only)"""

    name: str
    display_name: str


@dataclass
class Scenario:
    """Scenario info"""

    id: str  # pylint: disable=invalid-name
    name: str
    display_name: str
    parents: List[Parent]
    link: Optional[str]
    branch: Optional[str]

    def __hash__(self) -> int:
        return hash(self.id)
