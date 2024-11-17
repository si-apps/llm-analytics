import logging
import re
from typing import Optional, List, Generator, Tuple, Set, Dict

import sqlfluff
from sqlfluff.api import APIParsingError
from sqlfluff.core import SQLBaseError

_DIALECT = "duckdb"


def fix_sql(sql: str, column_names: Set[str] = None) -> str:
    sql = _convert_to_duckdb(sql)
    sql = _verify_columns_and_add_aliases(sql, column_names if column_names else set())
    sql = _remove_semicolon(sql)
    return sql


def _convert_to_duckdb(sql: str) -> Optional[str]:
    try:
        formatted_sql = sqlfluff.fix(sql, dialect="duckdb", rules=["L028"])
        return formatted_sql
    except SQLBaseError as e:
        logging.error(f"Error converting SQL: {e}")
        return None

def _remove_semicolon(sql: str) -> str:
    return re.sub(r'\s*;\s*$', '', sql, flags=re.MULTILINE)



def _update_col_name(name: str) -> str:
    name = name.replace('"', '')
    name = name.replace(' ', '_')
    name = name.replace('-', '_')
    name = name.replace('*', 'all')
    return name


def _create_alias_for_exp(exp: str) -> str:
    result = ""
    for c in exp:
        if c in [",", "(", ")", " "]:
            if len(result) > 0 and result[-1] != "_":
                result += "_"
        else:
            result += c.lower()
    return _update_col_name(result)


def _verify_columns_and_add_aliases(sql: str, column_names: Set[str]) -> Optional[str]:
    try:
        parse_tree = sqlfluff.parse(sql, dialect=_DIALECT)
    except APIParsingError as e:
        logging.error(f"SQL: {sql}\nError parsing SQL: {e}")
        return sql
    sql_statement = None
    for s in parse_tree["file"] if isinstance(parse_tree["file"], list) else [parse_tree["file"]]:
        if "statement" in s and "select_statement" in s["statement"]:
            sql_statement = s["statement"]["select_statement"]
            break
        if "statement" in s and "with_compound_statement" in s["statement"]:
            sql_statement = s["statement"]["with_compound_statement"]
            break
    if sql_statement is None:
        return sql
    renamed_cols: Dict[str, str] = {}
    for e in _get_elements(parse_tree, "column_reference", recursive=True):
        _fix_column_name(e[1], column_names, renamed_cols)
    if isinstance(sql_statement, dict):
        sql_statement = [{k: sql_statement[k]} for k in sql_statement]

    select_clause = _get_clause(sql_statement, "select")
    for e_name, e in _get_elements(select_clause):
        if e_name == "select_clause_element":
            if "alias_expression" not in e:
                if "column_reference" in e:
                    name = _get_name(e["column_reference"])
                    new_name = _update_col_name(name)
                    if name != new_name:
                        _update_alias(e, new_name)
                elif "wildcard_expression" not in e:
                    _update_alias(e, _create_alias_for_exp(_convert_to_text(e)))
            else:
                name = _get_name(e["alias_expression"])
                new_name = _update_col_name(name)
                if name != new_name:
                    renamed_cols[name] = new_name
                    _update_alias(e, new_name)
    order_by = _get_clause(sql_statement, "orderby")
    for e in order_by if order_by else []:
        if isinstance(e, dict) and "column_reference" in e:
            name = _get_name(e["column_reference"])
            if name in renamed_cols:
                e["column_reference"] = _update_col_name(_convert_to_text(e["column_reference"]))

    return _convert_to_text(parse_tree)

def _update_alias(e: dict, name: str):
    if "alias_expression" not in e:
        e["whitespace"] = ' '
    e["alias_expression"] = {
            "naked_identifier": {
                'keyword': 'AS',
                'whitespace': ' ',
                "simple_identifier": name,
            }
    }

def _get_clause(clause: list, name: str):
    for c in clause:
        if f"{name}_clause" in c:
            return c[f"{name}_clause"]
    return None

def _get_name(e: dict) -> str:
    if "naked_identifier" in e:
        return e["naked_identifier"]
    elif "quoted_identifier" in e:
        return e["quoted_identifier"].strip('"')
    else:
        raise ValueError(f"Unexpected column reference: {e}")


def _get_elements(clause, name: str = None, recursive: bool = False) ->  Generator[Tuple[str, any], None, None]:
    if isinstance(clause, dict):
        for k, v in clause.items():
            if name is None or name == k:
                yield k, v
            if recursive:
                for e in _get_elements(v, name, recursive):
                    yield e
    elif isinstance(clause, list):
        for e in clause:
            for k, v in e.items():
                if name is None or name == k:
                    yield k, v
                if recursive:
                    for ek in _get_elements(v, name, recursive):
                        yield ek

def _fix_column_name(col_ref: dict, cols: Set[str], renamed_cols: Dict[str, str]):
    if len(cols) == 0:
        return
    if "naked_identifier" in col_ref:
        col_name = col_ref["naked_identifier"]
        if not col_name in cols:
            for c in cols:
                if _remove_special_chars(c) == _remove_special_chars(col_name):
                    col_ref["naked_identifier"] = c
                    renamed_cols[col_name] = c
                    break

def _remove_special_chars(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', name)


def _convert_to_text(parse_tree: dict) -> str:
    result = ""
    for v in parse_tree.values():
        if isinstance(v, dict):
            result += _convert_to_text(v)
        elif isinstance(v, list):
            for e in v:
                result += _convert_to_text(e)
        else:
            result += v
    return result
