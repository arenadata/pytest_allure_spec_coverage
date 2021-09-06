"""Common plugin utilities"""

from typing import Optional

from _pytest.config import Config
from allure_pytest.listener import AllureListener


def allure_listener(config: Config) -> Optional[AllureListener]:
    """AllureListener plugin instance from pytest.Config"""

    return next(
        filter(
            lambda plugin: (isinstance(plugin, AllureListener)),
            dict(config.pluginmanager.list_name_plugin()).values(),
        ),
        None,
    )
