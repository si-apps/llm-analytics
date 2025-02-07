import csv
import json
import logging
import os.path
from typing import Generator, NamedTuple, List, Optional, Iterable

import duckdb

from question_to_sql import get_prompt
from sql_fixer import fix_sql
from utils import invoke_llm

_stats = {
    "passed": 0,
    "retry_passed": 0,
    "failed": 0,
    "retry_failed": 0,
    "sql_error": 0,
}
_tests_log = []


def validation_test_print_stats():
    logging.info(f"stats:\n{_stats}")
    logging.info(f"tests_log:\n{json.dumps(_tests_log, indent=4)}")


class ValidationTest(NamedTuple):
    group: str
    name: str
    question: str
    answer: list

def get_full_file_name(file: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file)


def get_test_names(file_name: str, test_group: str, test_name: str = None) -> Generator[ValidationTest, None, None]:
    with open(get_full_file_name(file_name)) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # noinspection PyTypeChecker
            if test_name and row["name"] != test_name:
                continue
            # noinspection PyTypeChecker
            yield ValidationTest(test_group, name=row["name"], question=row["question"],
                                 answer=eval(row["answer"]))


def _fetch_dict(con: duckdb.DuckDBPyConnection, query: str) -> Generator[dict, None, None]:
    handle = con.sql(query)
    while batch := handle.fetchmany(100):
        for row in batch:
            yield {c: row[idx] for idx, c in enumerate(handle.columns)}


def _data_to_str(data: Iterable) -> str:
    result = ""
    for row in data:
        result += str(row) + "\n"
    return result


def validate_test(test: ValidationTest, file: str, model_id: str = None):
    with duckdb.connect() as con:
        con.execute(f"CREATE TABLE my_table AS SELECT * FROM read_csv_auto('{get_full_file_name(file)}')")

        try:
            metadata = list(_fetch_dict(con, "SUMMARIZE my_table"))
            distinct_values_cols = [c["column_name"] for c in metadata if c["approx_unique"] <= 20]
        except Exception as e:
            logging.info(f"Got SQL error: {e}. Going to retry")
            metadata = list(_fetch_dict(con, "DESCRIBE my_table"))
            distinct_values_cols = []

        if len(distinct_values_cols) > 0:
            distinct_values_sql = "SELECT "
            for col in distinct_values_cols:
                distinct_values_sql += f'ARRAY_AGG(DISTINCT "{col}") AS "{col}",'
            distinct_values_sql = distinct_values_sql[:-1] + " FROM my_table"
            distinct_values = _data_to_str(_fetch_dict(con, distinct_values_sql))
        else:
            distinct_values = None
        sample_data = list(_fetch_dict(con, "SELECT * FROM my_table LIMIT 5"))
        prompt = get_prompt("my_table", test.question, _data_to_str(metadata), _data_to_str(sample_data),
                            distinct_values, hint=None)
        sql = invoke_llm(prompt, model_id if model_id else "anthropic.claude-instant-v1")
        sql = fix_sql(sql)
        try:
            sql_error = None
            result = con.execute(sql).fetchall()
        except Exception as e:
            sql_error = str(e)
            logging.info(f"Got SQL error: {sql_error}. Going to retry")
        if sql_error is not None:
            prompt = get_prompt("my_table", test.question, str(metadata), str(sample_data), hint=None,
                                previous_sql=sql, previous_error=sql_error)
            retry_sql = invoke_llm(prompt, model_id if model_id else "anthropic.claude-instant-v1")
            try:
                result = con.execute(retry_sql).fetchall()
            except Exception as e:
                _log_test(test, None, sql, sql_error, retry_sql, str(e))
                # assert False, f"Failed to execute SQL: {retry_sql}. Error: {e}"
                return
        else:
            retry_sql = None

        verification_error = _verify_result(test.answer, result)
        _log_test(test, verification_error, sql, sql_error, retry_sql, None)
        # if verification_error is not None:
        #     assert False, f"{verification_error}\nExpected: {test.answer}\nActual:   {result}\nSQL used: {sql}"


def _log_test(test: ValidationTest, verification_error: Optional[str], sql: str,
              sql_error: str, retry_sql: str, retry_sql_error: Optional[str]):
    if retry_sql_error:
        _stats["sql_error"] += 1
    elif verification_error:
        _stats["failed" if sql_error is None else "retry_failed"] += 1
    else:
        _stats["passed" if sql_error is None else "retry_passed"] += 1
    if verification_error or sql_error:
        _tests_log.append({
            "group": test.group,
            "name": test.name,
            "verification_error": verification_error,
            "sql": sql,
            "sql_error": sql_error,
            "retry_sql": retry_sql,
            "retry_sql_error": retry_sql_error
        })


def _verify_result(expected: List, actual: List) -> Optional[str]:
    if len(actual) != len(expected):
        return f"Wrong number of rows. Expected: {len(expected)}, Actual: {len(actual)}\nExpected: {expected}\nActual:   {actual}"
    for expected_row, result_row in zip(expected, actual):
        for expected_val, result_val in zip(expected_row, result_row):
            if isinstance(expected_val, float):
                expected_val = round(expected_val, 2)
                result_val = round(result_val, 2)
            if expected_val != result_val:
                return f"Wrong value. Expected: {expected_val}, Actual: {result_val}"
    return None

