import pytest

from utils import init_logging, init_env_from_file
from validation_tests_utils import get_test_names, ValidationTest, validate_test, validation_test_print_stats


@pytest.fixture(autouse=True, scope="module")
def set_evn():
    init_logging()
    init_env_from_file("aws.env.list")
    init_env_from_file("google.env.list")
    yield
    validation_test_print_stats()


@pytest.mark.parametrize("test", get_test_names("resources/validation/sales/basic-tests.csv",
                                                "sales", test_name=None))
@pytest.mark.parametrize("file", ["resources/validation/sales/sales_data.csv"])
@pytest.mark.parametrize("model_id", [
    "gemini-2.0-flash",
    "anthropic.claude-instant-v1",
])
def test_sales_validation(test: ValidationTest, file: str, model_id: str):
    validate_test(test, file, model_id)


@pytest.mark.parametrize("test", get_test_names("resources/validation/countries/countries-tests.csv",
                                                "countries", test_name=None))
@pytest.mark.parametrize("file", ["resources/validation/countries/countries.csv"])
@pytest.mark.parametrize("model_id", [
    "gemini-2.0-flash",
    "anthropic.claude-instant-v1",
])
def test_countries_validation(test: ValidationTest, file: str, model_id: str = None):
    validate_test(test, file, model_id)
