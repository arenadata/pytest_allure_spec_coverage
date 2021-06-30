"""pytest_allure_spec_coverage setup settings"""

from setuptools import setup, find_packages

setup(
    name="pytest_allure_spec_coverage",
    description="The pytest plugin aimed to display test coverage of the specs(requirements) in Allure",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    version="0.0.1",
    # the following makes a plugin available to pytest
    entry_points={"pytest11": ["pytest_allure_spec_coverage = pytest_allure_spec_coverage.plugin"]},
    # custom PyPI classifier for pytest plugins
    install_requires=["pytest", "allure-pytest"],
    classifiers=["Framework :: Pytest"],
)
