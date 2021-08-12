# Pytest Allure Spec Coverage

The pytest plugin aimed to display test coverage of the specs(requirements) in Allure

## Pre-commit hook

We are using black, pylint and pre-commit to care about code formatting and linting.

So you have to install pre-commit hook before you do something with code.

``` sh
pip install pre-commit # Or do it with your preffered way to install pip packages
pre-commit install
```

After this you will see invocation of black and pylint on every commit.

## Run tests

To run tests, execute within project root:

```bash
pip install -e .
pytest src/pytest_allure_spec_coverage --doctest-modules --alluredir tests/allure-results
pytest -s -v --showlocals --alluredir tests/allure-results
```
