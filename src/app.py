import logging
import os

from flask import Flask, render_template, request, jsonify

from question_to_sql import get_prompt

from sql_fixer import fix_sql
from utils import init_logging, init_creds_from_file, invoke_llm
from visitors_limit import VisitorsLimit

app = Flask(__name__)
visitors_limit = VisitorsLimit(100, 5, 1800)

_VERSION = "0.0.3"


@app.route('/ping')
def _ping():
    return jsonify({"status": "ok", "version": _VERSION})


@app.route('/')
def _app_main():
    return render_template("index.html",
                           advanced="advanced" in request.args,
                           gtag=os.environ.get("GTAG", ""),
                           version=_VERSION,
                           recaptcha_key=os.environ.get("RECAPTCHA_KEY", ""))


@app.route('/sql')
def _question_to_sql():
    visitor_id = request.args.get("visitor_id")
    if "RECAPTCHA_KEY" in os.environ:
        token = request.args["token"]
        if not _verify_recaptcha(token):
            return jsonify({"error": "Recaptcha verification failed"})

    if not visitors_limit.visit(visitor_id):
        return jsonify({"error": "Requests limit has been reached. Please try again later."})
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
    return jsonify({"sql": sql})


def _verify_recaptcha(token: str) -> bool:
    from urllib.parse import urlencode
    from urllib.request import urlopen
    import json
    remote_ip = request.remote_addr
    params = urlencode({
        'secret':  os.environ["RECAPTCHA_SECRET_KEY"],
        'response': token,
        'remote_ip': remote_ip,
    })
    data = urlopen('https://www.google.com/recaptcha/api/siteverify', params.encode('utf-8')).read()
    result = json.loads(data)
    print(result)
    success = result.get('success', None)
    return success


if __name__ == '__main__':
    init_logging()
    logging.info(f"Going to start the app. Version: {_VERSION}")
    init_creds_from_file()
    app.run(host="0.0.0.0", port=os.environ.get("APP_PORT", 5000))

