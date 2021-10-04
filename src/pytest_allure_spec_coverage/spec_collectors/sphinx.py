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
"""Sphinx spec collector implementation"""
import os
import warnings
from typing import Optional

from _pytest.config.argparsing import Parser
from docutils.core import publish_doctree
from docutils.utils import SystemMessage

from pytest_allure_spec_coverage.models.collector import Collector
from pytest_allure_spec_coverage.models.scenario import Scenario, Parent

PARENT_INDEX_PAGE = "index.rst"


class SphinxCollector(Collector):
    """
    Sphinx collector allows you to collect scenarios from .rst files located inside a project with tests
    At the moment, only title will be read from .rst file
    Template variables for title do not support

    Possible options:
        - sphinx_dir: required option, directory with the .rst scenarios
        - sphinx_endpoint: where is hosted your scenarios. Need to form scenario link. Optionally
        - default_branch: Need to form scenario link. "master" by default
            Sphinx can be hosted in different branches.
            For non-default branch scenario link be like {sphinx_endpoint}/{branch}/{scenario_url}
            But the branch is absent if tests run on default branch -
                in this case link be like {sphinx_endpoint}/{scenario_url}
    """

    sphinx_dir: str
    spec_endpoint: Optional[str]
    default_branch: str

    @staticmethod
    def addoption(parser: Parser):
        parser.addini("sphinx_dir", help="Directory with the .rst scenarios", type="string")
        parser.addini(
            "spec_endpoint",
            help="Where is hosted your scenarios. Need to form scenario link. Optionally",
            type="string",
            default=None,
        )
        parser.addini(
            "default_branch", help="Need to form scenario link. 'master' by default", type="string", default="master"
        )

    def setup_config(self):
        if not (sphinx_dir := self.config.get("sphinx_dir")):  # pylint: disable = superfluous-parens
            raise ValueError("Option sphinx_dir is required")
        if not os.path.isabs(sphinx_dir):
            sphinx_dir = os.path.join(self.config.root, sphinx_dir)
        if not os.path.exists(sphinx_dir):
            raise ValueError(f"Directory with sphinx specs {sphinx_dir} doesn't exists")

        self.sphinx_dir = sphinx_dir
        self.spec_endpoint = self.config.get("spec_endpoint")
        self.default_branch = self.config.get("default_branch")

    def collect(self):
        branch = os.getenv("BRANCH_NAME")
        scenarios = []
        parents_display_names = {}
        root_path = self.sphinx_dir.rsplit("/", maxsplit=1)[0]
        for root, _, files in os.walk(self.sphinx_dir):
            parent_name = root.replace(root_path, "").strip("/").replace("/", ".")
            parent_display_name = parent_name.rsplit(".", maxsplit=1)[-1]
            if PARENT_INDEX_PAGE in files:
                parent_display_name = (
                    self._get_title_from_rst(os.path.join(root, PARENT_INDEX_PAGE)) or parent_display_name
                )
                files.remove(PARENT_INDEX_PAGE)
            parents_display_names[parent_name] = parent_display_name

            for file in filter(lambda f: f.endswith(".rst"), files):
                name = file.rsplit(".", maxsplit=1)[0]
                display_name = self._get_title_from_rst(os.path.join(root, file)) or file
                parents = self._get_parents_by_fullname(parent_name, parents_display_names)
                scenarios.append(
                    Scenario(
                        id="/".join([*[p.name for p in parents[1:]], name]),  # Do not use root folder on scenario id
                        name=name,
                        display_name=display_name,
                        parents=parents,
                        link=self._create_link(name, parent_name, branch),
                        branch=branch,
                    )
                )
        return scenarios

    def _create_link(self, name, parent_name, branch):
        if not self.spec_endpoint:
            return None
        url = self.spec_endpoint
        if branch and branch != self.default_branch:
            branch = branch.replace("/", "_")
            url += f"/{branch}"
        url += f"/{parent_name.replace('.', '/')}"
        return f"{url}/{name}.html"

    @staticmethod
    def _get_title_from_rst(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
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
            warnings.warn(
                f"Templating vars in the title '{title}' are not supported. "
                f"Title will be used as is, without substitutions"
            )
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
