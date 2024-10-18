import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm/+esm";

async function instantiate(duckdb) {
  const CDN_BUNDLES = duckdb.getJsDelivrBundles(),
  bundle = await duckdb.selectBundle(CDN_BUNDLES),
  worker_url = URL.createObjectURL(
    new Blob([ `importScripts("${bundle.mainWorker}");` ], {
      type: "text/javascript"
    })
  );
  const worker = new Worker(worker_url),
  logger = new duckdb.ConsoleLogger("DEBUG"),
  db = new duckdb.AsyncDuckDB(logger, worker);

  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(worker_url);
  return db;
}
window.duck_db = await instantiate(duckdb);