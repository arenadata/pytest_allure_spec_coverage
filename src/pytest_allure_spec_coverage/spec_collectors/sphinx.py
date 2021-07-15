"""Sphinx spec collector implementation"""
import os
import warnings
from typing import Optional
from docutils.core import publish_doctree
from docutils.utils import SystemMessage

from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Scenario, Parent


class SphinxCollector(Collector):
    """
    Sphinx collector allows you to collect scenarios from .rst files
    At the moment, only title will be read from .rst file
    Template variables for title do not support

    Possible options:
        - sphinx_dir: required option where is places your scenarios
        - sphinx_endpoint: where is hosted your scenarios. Need to form scenario link. Optionally
    """

    sphinx_dir: str
    spec_endpoint: Optional[str]

    def validate_config(self):
        if "sphinx_dir" not in self.config:
            raise ValueError("Option sphinx_dir is required")
        sphinx_dir = self.config.get("sphinx_dir")
        if not os.path.exists(sphinx_dir):
            raise ValueError(f"Directory with sphinx specs {sphinx_dir} doesn't exists")

        self.sphinx_dir = sphinx_dir
        self.spec_endpoint = self.config.get("spec_endpoint")

    def collect(self):
        branch = os.getenv("BRANCH")
        scenarios = []
        parents_display_names = {}
        root_path = self.sphinx_dir.rsplit("/", maxsplit=1)[0]
        for root, _, files in os.walk(self.sphinx_dir):
            parent_name = root.replace(root_path, "").strip("/").replace("/", ".")
            parent_display_name = parent_name.rsplit(".", maxsplit=1)[-1]
            if "index.rst" in files:
                parent_display_name = self._get_title_from_rst(os.path.join(root, "index.rst")) or parent_display_name
                files.remove("index.rst")
            parents_display_names[parent_name] = parent_display_name

            for file in filter(lambda f: f.endswith(".rst"), files):
                name = file.rsplit(".", maxsplit=1)[0]
                display_name = self._get_title_from_rst(os.path.join(root, file)) or file

                scenarios.append(
                    Scenario(
                        name=name,
                        display_name=display_name,
                        parents=self._get_parents_by_fullname(parent_name, parents_display_names),
                        link=self._create_link(name, parent_name, branch),
                        branch=branch,
                    )
                )
        return scenarios

    def _create_link(self, name, parent_name, branch):
        if not self.spec_endpoint:
            return None
        url = self.spec_endpoint
        if branch:
            url += f"/{branch}"
        url += f"/{parent_name.replace('.', '/')}"
        return f"{url}/{name}.html"

    @staticmethod
    def _get_title_from_rst(file_path):
        with open(file_path, "r") as file:
            rst_lines = []
            line = file.readline()
            while line and line != "\n":
                rst_lines.append(line)
                line = file.readline()
        try:
            document = publish_doctree("".join(rst_lines))
        except SystemMessage:
            warnings.warn(f"Could not read title from spec file {file_path}. It will be skipped")
            return ""
        title = document.attributes.get("title")
        if title and "|" in title:
            warnings.warn(f"Templating vars in title '{title}' do not support.")
        return title

    @staticmethod
    def _get_parents_by_fullname(full_name: str, parents_display_names: dict):
        """
        >>> func = SphinxCollector._get_parents_by_fullname
        >>> func("scenario.first", {"scenario": "Scenario", "scenario.first": "First scenario"})
        [Parent(name='scenario', display_name='Scenario'), Parent(name='first', display_name='First scenario')]
        >>> func("scenario.first", {"scenario": "Scenario"})
        [Parent(name='scenario', display_name='Scenario')]
        """
        parents = []
        current_name = ""
        for short_name in full_name.split("."):
            current_name = ".".join([current_name, short_name]) if current_name else short_name
            if parents_display_names.get(current_name):
                parents.append(Parent(name=short_name, display_name=parents_display_names[current_name]))
        return parents
