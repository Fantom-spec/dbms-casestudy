import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { inr } from "../format.js";
import { openDB, addExpense, getAllExpenses, getPendingSyncCount, removeExpense } from "../idb.js";
import ExpenseForm from "../components/ExpenseForm.jsx";
import ExpenseTable from "../components/ExpenseTable.jsx";
import Summary from "../components/Summary.jsx";

const PAGE = 15;

export default function Tracker() {
  const [categories, setCategories] = useState([]);
  const [months, setMonths] = useState([]);
  const [month, setMonth] = useState("");
  const [filters, setFilters] = useState({ q: "", category: "" });
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const [summary, setSummary] = useState(null);
  const [pending, setPending] = useState(0);
  const [pendingLocal, setPendingLocal] = useState(0);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isNetworkError, setIsNetworkError] = useState(false);
  const [db, setDb] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const syncing = useRef(false);

  const load = useCallback(async () => {
    if (!month) return;
    setIsLoading(true);
    try {
      const [list, sum, pend] = await Promise.all([
        api.expenses({ ...filters, month, limit: PAGE, offset: page * PAGE }),
        api.summary(month),
        api.pending(),
      ]);
      setData(list);
      setSummary(sum);
      setPending(pend.count);
      setError("");
      setIsNetworkError(false);
    } catch (e) {
      const msg = e.isNetworkError ? "Offline or network error. " : "";
      setError(msg + e.message);
      setIsNetworkError(e.isNetworkError === true);
    } finally {
      setIsLoading(false);
    }
  }, [filters, month, page]);

  useEffect(() => {
    let mounted = true;
    Promise.all([api.categories(), api.months()])
      .then(([c, m]) => {
        if (!mounted) return;
        setCategories(c);
        setMonths(m);
        setMonth(m[0] || new Date().toISOString().slice(0, 7));
      })
      .catch((e) => {
        if (mounted) {
          // Fall back to current month if API fails
          setMonth(new Date().toISOString().slice(0, 7));
        }
      });
    return () => { mounted = false; };
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    // Ensure month is always set for immediate rendering
    if (!month) {
      setMonth(new Date().toISOString().slice(0, 7));
    }
  }, [month]);

  const refreshLocal = useCallback(async (d = db) => {
    if (!d) return;
    try { setPendingLocal(await getPendingSyncCount(d)); } catch {}
  }, [db]);

  useEffect(() => {
    openDB().then(setDb).catch((e) => console.warn("IndexedDB unavailable:", e));
  }, []);

  useEffect(() => {
    const on = () => setIsOnline(true);
    const off = () => setIsOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  // Push expenses queued while offline to the server, then drop them from the local queue.
  const syncPending = useCallback(async () => {
    if (!db || !isOnline || syncing.current) return;
    syncing.current = true;
    try {
      const items = (await getAllExpenses(db)).filter((i) => !i.synced);
      for (const item of items) {
        await api.create({ amount: item.amount, category: item.category, spent_on: item.spent_on, note: item.note ?? "" });
        await removeExpense(db, item.expense_id);
      }
      if (items.length) {
        setMonths(await api.months());
        await load();
      }
    } catch (e) {
      console.warn("Sync failed:", e.message);
    } finally {
      syncing.current = false;
      refreshLocal();
    }
  }, [db, isOnline, load, refreshLocal]);

  useEffect(() => { refreshLocal(); syncPending(); }, [db, isOnline, refreshLocal, syncPending]);

  const run = (fn) => async (...a) => {
    setIsLoading(true);
    try {
      await fn(...a);
      await load();
      return true;
    } catch (e) {
      const msg = e.isNetworkError ? "Offline or network error. " : "";
      setError(msg + e.message);
      setIsNetworkError(e.isNetworkError === true);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const save = run(async (body, id) => {
    if (id) {
      await api.update(id, body);
    } else {
      try {
        await api.create(body);
      } catch (e) {
        // Offline: keep the new expense locally and sync it later.
        if (!e.isNetworkError || !db) throw e;
        await addExpense(db, body);
        await refreshLocal();
      }
    }
    setEditing(null);
    try { setMonths(await api.months()); } catch {}
  });

  const remove = run(async (id) => {
    await api.remove(id);
  });

  const setBudget = run((b) => api.setBudget({ ...b, month }));

  return (
    <>
      <div className="bar-top">
        <span className="pill">{pending} pending sync</span>
        {pendingLocal > 0 && <span className="pill offline-pill">•{pendingLocal} saved offline</span>}
        <select value={month} onChange={(e) => { setMonth(e.target.value); setPage(0); }} aria-label="Month">
          {(months.includes(month) ? months : [month, ...months]).map((m) => <option key={m}>{m}</option>)}
        </select>
      </div>

      {error && (
        <div className="error" role="alert" onClick={() => setError("")}>
          {error}
          {isNetworkError && <button className="retry-btn" onClick={(e) => { e.stopPropagation(); load(); }}>Retry</button>}
        </div>
      )}
      {isLoading && <div className="loading">Loading…</div>}
      <Summary summary={summary} onBudget={setBudget} />

      <div className="grid">
        <section className="card">
          <h2>{editing ? "Edit expense" : "Add expense"}</h2>
          <ExpenseForm key={editing?.expense_id ?? "new"} categories={categories} initial={editing}
            onSubmit={save} onCancel={() => setEditing(null)} />
        </section>

        <section className="card">
          <div className="toolbar">
            <input placeholder="Search notes…" value={filters.q}
              onChange={(e) => { setFilters({ ...filters, q: e.target.value }); setPage(0); }} />
            <select value={filters.category}
              onChange={(e) => { setFilters({ ...filters, category: e.target.value }); setPage(0); }}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <ExpenseTable items={data.items} onEdit={setEditing} onDelete={(e) => {
            if (confirm(`Delete ${inr(e.amount)} ${e.category} expense?`)) remove(e.expense_id);
          }} />
          <div className="pager">
            <button disabled={page === 0 || isLoading} onClick={() => setPage(page - 1)}>‹ Prev</button>
            <span>{data.total ? `${page * PAGE + 1}–${Math.min((page + 1) * PAGE, data.total)} of ${data.total}` : "No results"}</span>
            <button disabled={(page + 1) * PAGE >= data.total || isLoading} onClick={() => setPage(page + 1)}>Next ›</button>
          </div>
        </section>
      </div>
    </>
  );
}
