import logging

from flask import Flask, render_template, request, jsonify

from question_to_sql import get_prompt

from sql_fixer import fix_sql
from utils import init_logging, init_creds_from_file, invoke_llm

app = Flask(__name__)

_VERSION = "0.0.2"


@app.route('/ping')
def _ping():
    return jsonify({"status": "ok", "version": _VERSION})


@app.route('/')
def _app_main():
    return render_template("index.html",
                           advanced="advanced" in request.args,
                           version=_VERSION)


@app.route('/sql')
def _question_to_sql():
    if "hint" in request.args and len(request.args["hint"]) > 0:
        hint = request.args["hint"]
    else:
        hint = None
    table_name = request.args.get("table_name")
    question = request.args.get("question")
    metadata = request.args.get("metadata")
    distinct_values = request.args.get("distinct_values", None)
    sample_data = request.args["sample_data"]
    previous_sql = request.args.get("previous_sql", None)
    previous_error = request.args.get("previous_error", None)
    prompt = get_prompt(table_name, question, metadata, sample_data, distinct_values, hint, previous_sql, previous_error)
    model_id = request.args["model_id"]
    logging.info(prompt)
    sql = invoke_llm(prompt, model_id)
    sql = fix_sql(sql)
    return sql


if __name__ == '__main__':
    init_logging()
    logging.info(f"Going to start the app. Version: {_VERSION}")
    init_creds_from_file()
    app.run(host="0.0.0.0")

