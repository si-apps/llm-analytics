from typing import Optional

_HINTS = [
    """Do NOT use sub-queries or any form of SELECT statement in the HAVING clause, as it is not supported by the DB. 
    Instead, use ORDER BY and LIMIT to get the top N rows. You can also use the WITH clause to create a temporary table.
    Here is an example:
    
    SELECT column_name
    FROM my_table
    GROUP BY column_name
    HAVING COUNT() = (SELECT MIN(column_name) FROM my_table)
    
    Can be changed to:
    WITH temp_table AS (
      SELECT min(column_name) as min_column_name
        FROM my_table)
    SELECT column_name
    FROM my_table CROSS JOIN temp_table
    WHERE column_name = min_column_name
    """,
    "The columns you used MUST BE in the metadata provided. Use the exact names from the <metadata> reference",
    # "Only for boolean columns, and not for any other column type Use COUNT_IF instead of SUM",
    "When a column has a hyphen or a space in it use double quotes to escape it",
    "Each column MUST HAVE an alias in english to make the output more readable",
    "When you are required to count records without a specific column, use COUNT(*)",
    # "When you are asked to return count of rows, for a specific column use COUNT(DISTINCT column_name)",
    "Do NOT use COUNT DISTINCT on column you group by",
    "You can also use the WITH clause to create a temporary table",
    "Unless explicitly stated otherwise, return ONLY the column(s) specifically requested in the question. "
    "Do not include count or any other columns in the final SELECT statement",
    "Aggregate function calls cannot be nested. For example you CANNOT use MIN(COUNT(*)) or MAX(SUM(column_name))",
]


def get_prompt(table_name: str, question: str, metadata: str, sample_data: str,
               distinct_values: str = None, hint: str = None, previous_sql: str = None,
               previous_error: str = None) -> str:
    prompt = f"""<instructions>
I have a table with the columns matching the json data below. The table name is {table_name}.
you MUST query from this table only. No other tables are available.
Please create a sql statement I can run on my db to get the answer to the question:
{question}
SUPER IMPORTANT: You MUST follow the ALL OF the following rules when constructing the SQL. 
Each one of them is important for the correct execution of the SQL - do not skip any of them:
{_format_hints(hint)}

{_get_retry_prompt(previous_sql, previous_error) if previous_sql else ""}
</instructions>
<formatting>
Please include a single sentence SQL comment before the statement, explaining the output of the statement. 
Start the comment with the prefix: /* Results for
Do not include any other comments in the SQL.
Return SQL only, without any other information. Use the duckdb SQL dialect.
</formatting>
        
Here is the table metadata:
<metadata>
{metadata}
</metadata>

{_get_distinct_values_prompt(distinct_values)}

this is the sample data:
<data>
{sample_data}
</data>
"""
    return prompt


def _get_distinct_values_prompt(distinct_values: Optional[str]) -> str:
    if distinct_values is None or distinct_values == "":
        return ""
    else:
        return f"""Here are columns with a closed set of unique values:
<distinct_values>
{distinct_values}
</distinct_values>"""


def _get_retry_prompt(previous_sql: str, previous_error: str) -> str:
    return f"""In previous attempt, the you created the the following sql:
{previous_sql}

The result was this error from the database:
{previous_error}        

Please use this information to correct the SQL and try again."""


def _format_hints(hint: str):
    result = ""
    for idx, h in enumerate(_HINTS):
        result += f"{idx + 1}. {h}\n"
    if hint:
        result += f"{len(_HINTS) + 1}. {hint}"
    return result

