"""Xdist shared storage between master and workers"""
import os
import shutil
import tempfile


class XdistSharedStorage:
    """Xdist shared storage implementation"""

    @staticmethod
    def is_xdist_master(config):
        """True if running on xdist master"""
        return not hasattr(config, "workerinput") and getattr(config.option, "dist", "no") != "no"

    @staticmethod
    def write(config, name, content):
        """
        Write shared data by name
        Used when need to share some from xdist workers to xdist master
        """
        shared_dir = config.workerinput["shared_directory"]
        with open(os.path.join(shared_dir, name), "w", encoding="utf-8") as file:
            file.write(str(content))

    @staticmethod
    def get(config, name):
        """
        Get shared data by name
        Used when need to share some from xdist workers to xdist master

        """
        shared_dir = config.shared_directory
        with open(os.path.join(shared_dir, name), "r", encoding="utf-8") as file:
            return file.read()

    def pytest_configure(self, config):
        """Create shared directory if xdist used"""
        if self.is_xdist_master(config):
            config.shared_directory = tempfile.mkdtemp()

    def pytest_unconfigure(self, config):
        """Remove shared directory if xdist used"""
        if self.is_xdist_master(config):
            shutil.rmtree(config.shared_directory)

    @staticmethod
    def pytest_configure_node(node):
        """Configure shared directory for xdist workers"""
        node.workerinput["shared_directory"] = node.config.shared_directory
