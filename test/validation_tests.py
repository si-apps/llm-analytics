import logging

import pytest

from utils import init_logging, init_creds_from_file
from validation_tests_utils import get_test_names, ValidationTest, validate_test, validation_test_print_stats


@pytest.fixture(autouse=True, scope="module")
def set_evn():
    init_logging()
    init_creds_from_file()
    yield
    validation_test_print_stats()


@pytest.mark.parametrize("test", get_test_names("resources/validation/sales/basic-tests.csv",
                                                "sales", test_name=None))
@pytest.mark.parametrize("file", ["resources/validation/sales/sales_data.csv"])
def test_sales_validation(test: ValidationTest, file: str):
    validate_test(test, file)


@pytest.mark.parametrize("test", get_test_names("resources/validation/countries/countries-tests.csv",
                                                "countries", test_name=None))
@pytest.mark.parametrize("file", ["resources/validation/countries/countries.csv"])
# @pytest.mark.parametrize("model_id", ["anthropic.claude-v2"])
def test_countries_validation(test: ValidationTest, file: str, model_id: str = None):
    validate_test(test, file, model_id)
