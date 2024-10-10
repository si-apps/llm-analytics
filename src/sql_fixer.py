import logging
import re
from typing import Optional

import sqlfluff
from sqlfluff.api import APIParsingError
from sqlfluff.core import SQLBaseError

_DIALECT = "duckdb"


def fix_sql(sql: str) -> str:
    sql = _convert_to_duckdb(sql)
    sql = _add_aliases(sql)
    return sql


def _convert_to_duckdb(sql: str) -> Optional[str]:
    try:
        formatted_sql = sqlfluff.fix(sql, dialect="duckdb", rules=["L028"])
        return formatted_sql
    except SQLBaseError as e:
        logging.error(f"Error converting SQL: {e}")
        return None


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
    return result


def _add_aliases(sql: str) -> Optional[str]:
    try:
        parse_tree = sqlfluff.parse(sql, dialect=_DIALECT)
    except APIParsingError as e:
        logging.error(f"SQL: {sql}\nError parsing SQL: {e}")
        return sql

    try:
        select_clause = None
        order_by_clause = None
        for s in parse_tree["file"] if isinstance(parse_tree["file"], list) else [parse_tree["file"]]:
            if "statement" in s and "select_statement" in s["statement"]:
                select_clause = s["statement"]["select_statement"]
                if isinstance(select_clause, list):
                    for c in select_clause:
                        if "select_clause" in c:
                            select_clause = c["select_clause"]
                        if "orderby_clause" in c:
                            order_by_clause = c["orderby_clause"]
                else:
                    select_clause = select_clause["select_clause"]
        if select_clause is None:
            return sql
        select_clause_elements = []
        for child in select_clause:
            if isinstance(child, dict) and "select_clause_element" in child:
                el = child["select_clause_element"]
            elif child == "select_clause_element":
                el = select_clause[child]
            else:
                continue
            select_clause_elements.append(el)
        idx = 0
        for e in select_clause_elements:
            if "alias_expression" not in e:
                name = None
                if "column_reference" in e:
                    if "quoted_identifier" in e["column_reference"]:
                        name = e["column_reference"]["quoted_identifier"]
                elif "wildcard_expression" in e:
                    continue
                else:
                    idx += 1
                    name = _create_alias_for_exp(_convert_to_text(e))
                if name is not None:
                    e["whitespace"] = ' '
                    e["alias_expression"] = {
                            "naked_identifier": {
                                'keyword': 'AS',
                                'whitespace': ' ',
                                "simple_identifier": name,
                            }
                    }
        renamed_cols = set()
        for e in [e for e in select_clause_elements if "alias_expression" in e]:
            if "naked_identifier" in e["alias_expression"]:
                if isinstance(e["alias_expression"]["naked_identifier"], str):
                    name = e["alias_expression"]["naked_identifier"]
                else:
                    name = e["alias_expression"]["naked_identifier"]["simple_identifier"]
            elif "quoted_identifier" in e["alias_expression"]:
                name = e["alias_expression"]["quoted_identifier"]
            else:
                assert False
            renamed_cols.add(name)
            name = _update_col_name(name)
            e["alias_expression"] = {
                "naked_identifier": {
                    'keyword': 'AS',
                    'whitespace': ' ',
                    "simple_identifier": name,
                }
            }
        if order_by_clause:
            for e in order_by_clause:
                if isinstance(e, dict) and "column_reference" in e:
                    name = _convert_to_text(e["column_reference"])
                    if name in renamed_cols:
                        e["column_reference"] = _update_col_name(_convert_to_text(e["column_reference"]))
        return _convert_to_text(parse_tree)
    except SQLBaseError as e:
        logging.error(f"SQL: {sql}\nError converting SQL: {e}")
        return None


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
