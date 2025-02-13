import re
import string
from time import sleep

import pytest

from app import app
from sql_fixer import fix_sql
from utils import get_project_folder, init_logging
from visitors_limit import VisitorsLimit


@pytest.fixture(autouse=True)
def set_evn(monkeypatch):
    init_logging()


def test_get_project_folder():
    assert get_project_folder().endswith("llm-analytics")

def _assert_ignore_whitespace(str1: str, str2: str):
    remove = string.punctuation + string.whitespace
    return str1.translate(remove) == str2.translate(remove)


class TestFixSql:
    def test_add_alias(self):
        assert (fix_sql("SELECT COUNT() FROM my_table")
                == "SELECT COUNT() AS count_ FROM my_table")
        assert (fix_sql("SELECT COUNT(DISTINCT col) FROM my_table")
                == "SELECT COUNT(DISTINCT col) AS count_distinct_col_ FROM my_table")
        assert (fix_sql("SELECT SUBSTRING(col, 1, 10) FROM my_table")
                == "SELECT SUBSTRING(col, 1, 10) AS substring_col FROM my_table")

    def test_column_reference(self):
        assert (fix_sql("SELECT customer FROM my_table")
                == "SELECT customer FROM my_table")

    def test_column_with_quotes(self):
        assert (fix_sql('SELECT "customer name" FROM my_table')
                == 'SELECT "customer name" AS customer_name FROM my_table')

    def test_column_with_quotes_and_space(self):
        assert (fix_sql('SELECT "customer name" FROM my_table')
                == 'SELECT "customer name" AS customer_name FROM my_table')

    def test_multi_statements(self):
        assert (fix_sql('/* this is a comment*/\n\nSELECT customer FROM my_table')
                == '/* this is a comment */ SELECT customer FROM my_table')

    def test_hyphen(self):
        assert (fix_sql('SELECT "customer-name" FROM my_table')
                == 'SELECT "customer-name" AS customer_name FROM my_table')

    def test_hyphen_in_function(self):
        _assert_ignore_whitespace (fix_sql("""SELECT region, COUNT(DISTINCT "region-code") AS "number of countries"
FROM my_table
GROUP BY region
HAVING COUNT(DISTINCT "region-code") > 0"""),
    """SELECT region, COUNT(DISTINCT "region-code") AS number_of_countries
FROM my_table
GROUP BY region
HAVING COUNT(DISTINCT "region-code") > 0""")

    def test_select_star(self):
        assert (fix_sql('SELECT * FROM my_table')
                == 'SELECT * FROM my_table')

    def test_count_star(self):
        assert (fix_sql('SELECT COUNT(*) FROM my_table')
                == 'SELECT COUNT(*) AS count_star_ FROM my_table')


    def test_order_by(self):
        assert (fix_sql('SELECT SUBSTRING(name, 1, 1) AS "some-col" FROM my_table ORDER BY "some-col" LIMIT 5')
                == 'SELECT SUBSTRING(name, 1, 1) AS some_col FROM my_table ORDER BY "some_col" NULLS FIRST LIMIT 5')
        assert (fix_sql('SELECT * FROM my_table ORDER BY "customer-name" LIMIT 5')
                == 'SELECT * FROM my_table ORDER BY "customer-name" NULLS FIRST LIMIT 5')

    def test_remove_semicolon(self):
        expected = "SELECT * FROM my_table"
        assert fix_sql("SELECT *\nFROM my_table;") == expected
        assert fix_sql("SELECT * FROM my_table;    ") == expected
        assert fix_sql("SELECT * FROM my_table    ;    ") == expected
        assert fix_sql("SELECT *\nFROM my_table    ;   \n    ") == expected
        assert fix_sql("SELECT * FROM my_table\n    ;   \n    ") == expected


    def test_matching_column_name(self):
        assert fix_sql("SELECT col1, col2 FROM my_table", {"col1", "col2"}) == "SELECT col1, col2 FROM my_table"

    def test_similar_column_name(self):
        assert fix_sql("SELECT the_col1, col2 FROM my_table", {"thecol1", "col2"}) == 'SELECT thecol1, col2 FROM my_table'

    def test_similar_column_name_with_order_by(self):
        assert fix_sql("SELECT the_col1, col2 FROM my_table ORDER BY the_col1", {"thecol1", "col2"}) == \
               'SELECT thecol1, col2 FROM my_table ORDER BY thecol1 NULLS FIRST'


class TestVisitorsLimit:
    def test_visitors_limit(self):
        vl = VisitorsLimit(5, 2, 2)
        assert vl.visit("1")
        assert vl.visit("1")
        assert not vl.visit("1")
        assert vl.visit("2")
        assert vl.visit("2")
        assert not vl.visit("2")
        assert vl.visit("3")
        assert not vl.visit("3")
        sleep(3)
        assert vl.visit("1")
        assert vl.visit("4")

    def test_single_visitor_limit(self):
        vl = VisitorsLimit(5, 2, 2)
        assert vl.visit("1")
        assert vl.visit("1")
        assert not vl.visit("1")
        sleep(3)
        assert vl.visit("1")



class TestFlaskApp:
    def test_ping(self):
        result = app.test_client().get("/ping").json
        assert result["status"] == "ok"
        assert re.match(r"\d+\.\d+\.\d+", result["version"]) is not None

    def test_main_html(self):
        result = app.test_client().get("/")
        assert result.status_code == 200
        html = result.text
        assert html.startswith("<!DOCTYPE html>") and html.endswith("/html>")

