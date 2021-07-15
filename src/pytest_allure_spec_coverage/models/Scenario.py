from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Parent:
    name: str
    display_name: str


@dataclass
class Scenario:
    name: str
    display_name: str
    parents: List[Parent]
    link: Optional[str]
    branch: Optional[str]
