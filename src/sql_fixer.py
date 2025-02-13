import logging
import re
from typing import Optional, Set, Dict

import sqlglot.expressions as expr

import sqlglot

_DIALECT = "duckdb"


def fix_sql(sql: str, column_names: Set[str] = None) -> str:
    sql = _convert_to_duckdb(sql)
    sql = _verify_columns_and_add_aliases(sql, column_names if column_names else set())
    sql = _remove_semicolon(sql)
    return sql


def _convert_to_duckdb(sql: str) -> Optional[str]:
    try:
        converted_sql = sqlglot.transpile(sql, write=_DIALECT)
        return converted_sql[0]
    except sqlglot.errors.ParseError as e:
        logging.error(f"Error converting SQL: {e}")
        return None

def _remove_semicolon(sql: str) -> str:
    return re.sub(r'\s*;\s*$', '', sql, flags=re.MULTILINE)



def _update_col_name(name: str) -> str:
    name = name.replace('"', '')
    name = name.replace(' ', '_')
    name = name.replace('-', '_')
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
        parse_tree = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError as e:
        logging.error(f"SQL: {sql}\nError parsing SQL: {e}")
        return sql
    updated_aliases: Dict[str, str] = {}
    s = parse_tree.find(expr.Select)
    for e in s.expressions:
        new_name = None
        if isinstance(e, expr.Condition) and e.alias == "":
            new_name = _get_key(e)
        if new_name and new_name != e.name:
            e.replace(expr.Alias(this=e.copy(), alias=new_name))
        if isinstance(e, expr.Alias):
            new_name = _update_col_name(e.alias)
            if new_name != e.alias:
                e.replace(expr.Alias(this=e.this, alias=_update_col_name(e.alias)))
                updated_aliases[e.alias] = new_name
    _fix_column_names(parse_tree, column_names, updated_aliases)
    for o in parse_tree.find_all(expr.Order):
        identifier = o.find(expr.Column).find(expr.Identifier)
        if identifier.name in updated_aliases:
            identifier.replace(expr.Identifier(this=updated_aliases[identifier.name],
                                                         quoted=identifier.quoted))
    return s.sql(dialect=_DIALECT)

def _get_key(e: expr.Expression) -> str:
    if isinstance(e, expr.Column):
        return _update_col_name(e.name)
    if e.this is not None:
        sub_key = _get_key(e.this)
    elif len(e.expressions):
        sub_key = "_".join([_get_key(c) for c in e.expressions])
        sub_key += "_"
    else:
        sub_key = ""
    return f"{e.key}_{sub_key}"


def _remove_special_chars(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', name)


def _fix_column_names(parse_tree: expr.Expression, cols: Set[str], renamed_cols: Dict[str, str]):
    if len(cols) == 0:
        return
    for col_ref in parse_tree.find_all(expr.Column):
        identifier = col_ref.find(expr.Identifier)
        if not identifier.name in cols:
            for c in cols:
                if _remove_special_chars(c) == _remove_special_chars(identifier.name):
                    renamed_cols[identifier.name] = c
                    identifier.replace(expr.Identifier(this=c, quoted=identifier.quoted))
                    break


