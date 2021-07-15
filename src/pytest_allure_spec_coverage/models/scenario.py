"""Models for scenario"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Parent:
    """Parent scenario info"""

    name: str
    display_name: str


@dataclass
class Scenario:
    """Scenario info"""

    name: str
    display_name: str
    parents: List[Parent]
    link: Optional[str]
    branch: Optional[str]
