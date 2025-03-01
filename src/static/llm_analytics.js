let db = null;
let table_loaded = false;
let sqls = [null, null, null];
let _visitor_id = null;
let charts = [null, null, null];

async function create_db(file_url, file_name) {
    const cnn = await window.duck_db.connect();
    let table_name = get_table_name(0);
    table_loaded = false;
    await cnn.query("DROP TABLE IF EXISTS " + table_name);
    let convert_to_jsonl = false;
    if (file_name.endsWith(".xlsx") || file_name.endsWith(".xls")) {
        file_url = await xlsxToJsonlFile(file_url);
        if (file_url != null) {
            console.log("Loading Excel file as JSONL")
            convert_to_jsonl = true;
        }
        else {
            console.log("Error converting Excel file to JSONL")
        }
    }
    if (file_name.endsWith(".jsonl") || convert_to_jsonl) {
        window.duck_db.registerFileURL(table_name, file_url, 4, false);
         let load_query = `CREATE TABLE ${table_name} AS
                        SELECT * FROM read_json("${table_name}",format=newline_delimited,
                                                auto_detect=true, sample_size=100000)`
        await cnn.query(load_query);
        table_loaded = true;
    }
    else if (file_name.endsWith(".csv")) {
        window.duck_db.registerFileURL(table_name, file_url, 4, false);
        let load_query = `CREATE TABLE ${table_name} AS
                    SELECT * FROM read_csv("${table_name}", auto_detect=true, sample_size=100000)`
        await cnn.query(load_query);
        table_loaded = true;
    }
    else {
        console.log("Unsupported file format: " + file_name)
    }
    console.log("DB Initialized")
    return cnn
}

async function get_file_record_count(){
    if (!table_loaded)
        return 0
    else {
        let table_name = get_table_name(0);
        return JSON.parse(await db.query(`SELECT COUNT(1) AS cnt
                                          FROM ${table_name}`))[0]["cnt"]
    }
}

async function create_metadata_buttons(index) {
    if (!table_loaded) {
        clear_metadata_buttons()
        return
    }
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
    if (column_name.includes(" ") || column_name.includes("-")) {
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
    set_status("file", "")
    for (let i = 0; i < 3; i++) {
        clear_results_and_status(i);
    }
    let file = document.getElementById("file_input").files[0];
    await select_file(file);
}

async function select_file(file){
    let url = (window.URL || window.webkitURL).createObjectURL(file);
    try {
        update_loader("file", true);
        db = await create_db(url, file.name);
        let record_count = await get_file_record_count()
        uploadText.textContent = `${file.name} selected (${record_count.toLocaleString()} records)`;
        await create_metadata_buttons(0)
    }
    finally {
        update_loader("file", false);
    }
}

async function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();

        let index = parseInt(event.target.id[event.target.id.length - 1]);
        await ask_question(index);
    }
}

async function ask_question(index) {
    if (!table_loaded) {
        set_status(index, "Please upload a file first");
        return
    }
    let table_name = get_table_name(index);
    clear_results_and_status(index)

    if (document.getElementById("file_input").files.length === 0) {
        set_status("file", "Please upload a file first");
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
        await drill_down(index);
    }
}

function clear_results_and_status(index) {
    for (let i = index; i < charts.length; i++) {
        document.getElementById(`results-table-${i}`).outerHTML = `<div class=\"results\" id=\"results-table-${i}\"></div>`
        if (charts[i] != null)
            charts[i].destroy();
        document.getElementById(`my-chart-${i}`).display = 'None';
        set_status(index, "")
        if (i < sqls.length - 1) {
            document.getElementById(`drill_down-${i}`).style.display = 'None';
        }
        if (i > index) {
            sqls[i] = null;
            document.getElementById(`question_input-${i}`).value = "";
        }
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
        show_data(index, text_data, question)
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
            show_data(index, text_data, question)
            return retry_sql;
        } catch (e) {
            set_status(index, e.toString())
        }
    }
    return null
}

function show_data(index, text_data, question) {
    function _get_chart_type(question) {
        if (question.toLowerCase().includes("pie")) {
            return "pie"
        }
        else if (question.toLowerCase().includes("line chart")) {
            return "line"
        }
        else if (question.toLowerCase().includes("bar chart")) {
            return "bar"
        }
        else {
            return null
        }
    }

    try {

        let json_data = JSON.parse(text_data);

        let chart_show = false;
        let chart_type = _get_chart_type(question);
        if (chart_type != null) {
            chart_show =  show_chart_data(index, json_data, chart_type);
            if (chart_show)
                document.getElementById(`my-chart-${index}`).style.display = 'block';
        }
        if (!chart_show)
            show_table_data(index, json_data);
    } catch (e) {
        set_status(index, e)
    }
}

function show_table_data(index, json_data) {
    new Tabulator(`#results-table-${index}`, {
            data: json_data,
            autoColumns: true,
            pagination: "local",
            paginationSize: 20,
            layout: "fitColumns"
        });
}

function get_chart_columns(json_data) {
    function _find_col_by_type(data, col_type) {
        for (let key in line) {
            if (typeof line[key] === col_type)
                return key
        }
        return null
    }
    if (json_data.length === 0)
        return []
    let line = json_data[0]
    if (line.length <= 1)
        return []
    let label_col = _find_col_by_type(line, "string")
    let value_col = _find_col_by_type(line, "number")

    if (label_col == null || value_col == null) {
        let keys = Object.keys(line);
        return [keys[0], keys[1]];
    }
    else
        return [label_col, value_col]
}

function show_chart_data(index, json_data, chart_type) {
    let canvas = document.getElementById(`my-chart-${index}`)
    if (json_data.length === 0)
        return false
    let chart_cols = get_chart_columns(json_data)
    if (chart_cols.length === 0)
        return false;
    console.log(chart_cols);
    const labels = json_data.map(item => item[chart_cols[0]]);
    const values = json_data.map(item => item[chart_cols[1]]);
    charts[index] = new Chart(canvas, {
        type: chart_type,
        data: {
            labels: labels,
            datasets: [{
                label: chart_cols[0],
                data: values
            }]
        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
        }
    });
    return true
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

async function xlsxToJsonlFile(blobUrl) {
    try {
        const response = await fetch(blobUrl);
        const blob = await response.blob(); // Convert response to a Blob
        const reader = new FileReader();

        return new Promise((resolve, reject) => {
            reader.onload = function (e) {
                const data = new Uint8Array(e.target.result);
                const workbook = XLSX.read(data, { type: 'array' });

                const sheet = workbook.Sheets[workbook.SheetNames[0]];
                const jsonData = XLSX.utils.sheet_to_json(sheet);
                if (jsonData.length === 0)
                    resolve(null);
                const jsonlData = jsonData.map(row => JSON.stringify(row)).join('\n');
                const jsonlBlob = new Blob([jsonlData], { type: "application/json" });
                const jsonlBlobUrl = URL.createObjectURL(jsonlBlob);
                resolve(jsonlBlobUrl);
            };

            reader.onerror = function (error) {
                reject("Error reading the Blob: " + error);
            };

            reader.readAsArrayBuffer(blob);
        });
    } catch (error) {
        console.error("Error fetching or processing the Blob URL:", error);
        throw error;
    }
}