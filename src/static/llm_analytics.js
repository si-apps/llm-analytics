let db = null
let sqls = [null, null, null]
let _visitor_id = null;

async function create_db(file_url, file_name) {
    const db = await window.duck_db.connect();
    let table_name = get_table_name(0);
    await db.query("DROP TABLE IF EXISTS " + table_name);
    window.duck_db.registerFileURL(table_name, file_url, 4, false);
    if (file_name.endsWith(".jsonl")) {
        let load_query = `CREATE TABLE ${table_name} AS
                    SELECT * FROM read_json("${table_name}",format =newline_delimited,
                                            auto_detect=true, sample_size=100000)`
        await db.query(load_query);
    }
    else if (file_name.endsWith(".csv")) {
        let load_query = `CREATE TABLE ${table_name} AS
                    SELECT * FROM read_csv("${table_name}", auto_detect=true, sample_size=100000)`
        await db.query(load_query);
        let record_count = JSON.parse(await db.query(`SELECT COUNT(1) AS cnt FROM ${table_name}`))[0]["cnt"]
        document.getElementById("record_count").innerText = "(" +
            record_count.toLocaleString() + " records)";
    }
    else {
        console.log("Unsupported file format: " + file_name)
    }
    console.log("DB Initialized")
    return db
}

async function create_metadata_buttons(index) {
    let metadata = JSON.parse(await db.query(`DESCRIBE ${get_table_name(index)}`));
    let column_names = metadata.map(column => column["column_name"]);
    let html = "";
    column_names.forEach((column_name) => {
        html += `<button class="column_button" onclick="column_click(${index},'${column_name}')">${column_name}</button>`;
    });
    document.getElementById(`metadata-${index}`).innerHTML = html;
}

function clear_metadata_buttons() {
    for (let i = 0; i < 3; i++) {
        document.getElementById(`metadata-${i}`).innerHTML = "";
    }
}

function column_click(index, column_name) {
    if (column_name.includes(" ")) {
        column_name = `"${column_name}"`
    }
    document.getElementById(`question_input-${index}`).value += column_name + " ";
    document.getElementById(`question_input-${index}`).focus();
}

function update_loader(index, visible) {
    document.getElementById("loader-" + index.toString()).style.display = visible ? "block" : "none";
}

async function file_change() {
    clear_metadata_buttons();
    for (let i = 0; i < 3; i++) {
        clear_results_and_status(i);
    }
    let file = document.getElementById("file").files[0];
    let url = (window.URL || window.webkitURL).createObjectURL(file);
    try {
        update_loader(0, true);
        db = await create_db(url, file.name);
        await create_metadata_buttons(0)
    }
    finally {
        update_loader(0, false);
    }
}

async function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();

        let index = parseInt(event.target.id[event.target.id.length - 1]);
        let table_name = get_table_name(index);
        clear_results_and_status(index)

        if (document.getElementById("file").files.length === 0) {
            set_status(index, "Please upload a file first");
            return
        }
        if (db == null) {
            set_status(index, "Database not initialized. Please try again in a few seconds");
            return null
        }
        try {
            update_loader(index, true);
            sqls[index] = await run_query(index, table_name);
        }
        finally {
            update_loader(index, false);
        }
        if ((sqls[index] != null) && (index < sqls.length - 1)) {
            document.getElementById(`drill_down_button-${index}`).style.display = 'block';
        }
    }
}

function clear_results_and_status(index) {
    document.getElementById(`results-table-${index}`).outerHTML = `<div class=\"results\" id=\"results-table-${index}\"></div>`
    set_status(index, "")
    if (index < sqls.length - 1) {
        document.getElementById(`drill_down-${index}`).style.display = 'None';
        document.getElementById(`drill_down_button-${index}`).style.display = 'none';
    }
}

function set_status(index, text) {
    document.getElementById(`status-${index}`).innerText = text
}

function get_table_name(index) {
    return `my_table_${index}`
}


async function run_query(index) {
    if (_visitor_id == null) {
        init_device_fingerprint()
    }
    const my_url = new URL(window.location.origin + "/sql");
    let token = await get_captcha_token()
    my_url.searchParams.append("token", token);
    let question = document.getElementById(`question_input-${index}`).value;
    let table_name = get_table_name(index);
    my_url.searchParams.append("visitor_id", _visitor_id);
    my_url.searchParams.append("question", question);
    my_url.searchParams.append("table_name", table_name);
    my_url.searchParams.append("hint", document.getElementById("hint").value);
    let num_samples = document.getElementById("num_samples").value;
    if (num_samples > 0)
        my_url.searchParams.append("sample_data", await db.query(
            `SELECT * FROM ${table_name} LIMIT ${num_samples}`));

    let metadata;
    try {
        metadata = await db.query(`SUMMARIZE ${table_name}`);
        metadata = JSON.parse(metadata).map(column => {
            return {
                column_name: column["column_name"],
                column_type: column["column_type"],
                approx_unique: column["approx_unique"]
            };
        });
    } catch (e) {
        console.log("Error in SUMMARIZE: " + e.toString())
        metadata = JSON.parse(await db.query(`DESCRIBE ${table_name}`));
    }
    my_url.searchParams.append("metadata", JSON.stringify(metadata));
    let cols_with_distinct_values = [];
    metadata.forEach((column) => {
        if (column["approx_unique"] <= 20) {
            cols_with_distinct_values.push(column["column_name"]);
        }
    });
    if (cols_with_distinct_values.length > 0) {
        let distinct_values_sql = "SELECT "
        cols_with_distinct_values.forEach((col) => {
            distinct_values_sql += `ARRAY_AGG(DISTINCT "${col}") AS "${col}",`
        });
        distinct_values_sql = distinct_values_sql.slice(0, -1) + ` FROM ${table_name}`;
        my_url.searchParams.append("distinct_values", await db.query(distinct_values_sql));
    }
    my_url.searchParams.append("model_id", document.getElementById("model_id").value);
    let response = await fetch(my_url.href);
    let json_response = await response.json();
    if (json_response["error"] != null) {
        set_status(index, json_response["error"]);
        return null
    }

    let sql = json_response["sql"];

    let COMMENT_REGEXP = "\\s*\\/\\*((?:.|\\n)*)\\*\\/"
    let match = sql.match(COMMENT_REGEXP);
    if (match) {
        set_status(index, match[1]);
    }
    let previous_error = null
    let previous_sql = sql
    try {
        let text_data = await db.query(sql);
        show_data(index, text_data)
        return sql;
    } catch (e) {
        previous_error = e.toString()
        console.log(previous_error)
        console.log("Going to retry")
    }
    if (previous_error != null) {
        my_url.searchParams.append("previous_error", previous_error);
        my_url.searchParams.append("previous_sql", previous_sql);
        let retry_response = await fetch(my_url.href);
        let retry_sql = await retry_response.text();
        try {
            let text_data = await db.query(retry_sql);
            show_data(index, text_data)
            return retry_sql;
        } catch (e) {
            set_status(index, e.toString())
        }
    }
    return null
}

function show_data(index, text_data) {
    try {

        let json_data = JSON.parse(text_data);

        new Tabulator(`#results-table-${index}`, {
            data: json_data,
            autoColumns: true,
            pagination: "local",
            paginationSize: 20,
            layout: "fitColumns"
        });
    } catch (e) {
        set_status(index, e)
    }
}

async function drill_down(index) {
    document.getElementById(`drill_down-${index}`).style.display = 'block';
    let table_name = get_table_name(index + 1)
    console.log("Drilling down to " + table_name)
    await db.query(`DROP TABLE IF EXISTS ${table_name}`);
    let load_query_sql = `CREATE TABLE ${table_name} AS (${sqls[index]})`;
    await db.query(load_query_sql);
    await create_metadata_buttons(index + 1)
}

function init_device_fingerprint() {
    const fpPromise = import('https://openfpcdn.io/fingerprintjs/v4')
        .then(FingerprintJS => FingerprintJS.load())
    fpPromise
        .then(fp => fp.get())
        .then(result => {
            _visitor_id = result.visitorId;
        })
}