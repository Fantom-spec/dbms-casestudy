import { useEffect, useState } from "react";
import { api } from "../api.js";

const METRICS = [
  ["single_insert_ms", "Single insert + commit", "ms"],
  ["lookup_by_id_ms", "Lookup by id", "ms"],
  ["monthly_sum_ms", "Monthly sum (GROUP BY)", "ms"],
  ["bulk_insert_ms", "Bulk insert", "ms"],
];
const SIZE_OPTS = [1000, 10000, 100000];
const fmt = (v) => (v == null ? "—" : v < 0.1 ? v.toFixed(4) : v < 10 ? v.toFixed(3) : v.toFixed(1));

function Bars({ title, sqlite, pg }) {
  const max = Math.max(sqlite ?? 0, pg ?? 0) || 1;
  const row = (label, v, cls) => (
    <div className="brow">
      <span className="blabel">{label}</span>
      <div className="btrack">{v != null && <div className={"bfill " + cls} style={{ width: Math.max(2, (v / max) * 100) + "%" }} />}</div>
      <span className="bval">{fmt(v)} ms</span>
    </div>
  );
  const ratio = sqlite && pg ? (pg > sqlite ? `SQLite ${(pg / sqlite).toFixed(1)}× faster` : `PostgreSQL ${(sqlite / pg).toFixed(1)}× faster`) : "";
  return (
    <div className="metric">
      <div className="mtitle"><span>{title}</span><span className="muted">{ratio}</span></div>
      {row("SQLite", sqlite, "s")}
      {row("PostgreSQL", pg, "p")}
    </div>
  );
}

export default function Compare() {
  const [status, setStatus] = useState(null);
  const [sizes, setSizes] = useState([1000, 10000]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.compareStatus().then(setStatus).catch((e) => setError(e.message)); }, []);

  const run = async () => {
    setBusy(true); setError("");
    try { setRes(await api.compareRun(sizes)); setStatus(null); api.compareStatus().then(setStatus); }
    catch (e) { setError(e.message); }
    setBusy(false);
  };
  const toggle = (n) => setSizes(sizes.includes(n) ? sizes.filter((x) => x !== n) : [...sizes, n].sort((a, b) => a - b));
  const pgOn = res ? res.postgres.available : status?.available;

  return (
    <>
      <section className="card">
        <h2>Embedded vs client-server database</h2>
        <p className="muted">Runs the same operations on this machine against SQLite (in-process) and PostgreSQL (server). Benchmarks use scratch tables only, never your expense data.</p>
        <div className={"status " + (pgOn ? "ok" : "off")}>
          {status == null ? "Checking PostgreSQL…" : pgOn
            ? `PostgreSQL connected (v${status.version ?? res?.postgres.version})`
            : `PostgreSQL not available: ${status.reason}. SQLite results will still run. Set PG_DSN and restart the backend.`}
        </div>
        <div className="row wrap">
          <span className="muted">Dataset sizes:</span>
          {SIZE_OPTS.map((n) => (
            <label key={n} className="chk"><input type="checkbox" checked={sizes.includes(n)} onChange={() => toggle(n)} />{n.toLocaleString()} rows</label>
          ))}
          <button className="primary" disabled={busy || !sizes.length} onClick={run}>{busy ? "Running benchmarks…" : "Run comparison"}</button>
        </div>
        {sizes.includes(100000) && <p className="muted small">100,000 rows can take 10+ seconds on PostgreSQL.</p>}
        {error && <div className="error" onClick={() => setError("")}>{error}</div>}
      </section>

      {res && (
        <>
          <div className="legend"><span><i className="sw s" /> SQLite</span><span><i className="sw p" /> PostgreSQL</span></div>
          {res.sizes.map((n, i) => (
            <section className="card" key={n}>
              <h2>{n.toLocaleString()} rows <span className="muted small">(median of 20 runs)</span></h2>
              <div className="metrics">
                {METRICS.map(([k, label]) => <Bars key={k} title={label} sqlite={res.sqlite[i][k]} pg={res.pg?.[i][k]} />)}
              </div>
            </section>
          ))}

          <div className="grid2">
            <section className="card">
              <h2>Concurrent writers</h2>
              <p className="muted small">{res.concurrency.writers} threads × {res.concurrency.per_writer} inserts each, total wall time.</p>
              <div className="metrics one">
                <Bars title="Total time" sqlite={res.concurrency.sqlite_ms} pg={res.concurrency.postgres_ms} />
              </div>
              <p className="small">SQLite allows one writer at a time; PostgreSQL runs true concurrent sessions.</p>
            </section>
            <section className="card">
              <h2>Server unavailable</h2>
              <p><span className="tag ok">SQLite</span> {res.availability.sqlite}</p>
              <p><span className="tag bad">PostgreSQL</span> {res.availability.postgres ?? "Not tested (PostgreSQL not configured)"}</p>
              <h2 className="mt">Setup effort</h2>
              <p><span className="tag ok">SQLite</span> {res.setup.sqlite}</p>
              <p><span className="tag bad">PostgreSQL</span> {res.setup.postgres}</p>
            </section>
          </div>
          <p className="muted small">Localhost numbers. On a real phone a PostgreSQL server is across the network, which adds tens of ms per call.</p>
        </>
      )}
    </>
  );
}
