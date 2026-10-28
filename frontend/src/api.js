async function req(path, opts = {}, retries = 2, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  try {
    const res = await fetch("/api" + path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      let msg = res.statusText;
      try {
        const d = await res.json();
        msg = Array.isArray(d.detail) ? d.detail.map((e) => e.msg).join("; ") : d.detail || msg;
      } catch {}
      const err = new Error(msg);
      err.status = res.status;
      err.isApiError = true;
      throw err;
    }
    return res.status === 204 ? null : res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e.name === "AbortError" || e.name === "TimeoutError") {
      const err = new Error("Request timed out");
      err.isNetworkError = true;
      throw err;
    }
    if (!e.isApiError && retries > 0 && !opts.method) {
      // Retry only GET requests on network errors
      await new Promise(r => setTimeout(r, 500));
      return req(path, opts, retries - 1, timeoutMs);
    }
    if (!e.isApiError) {
      const err = new Error("Network error: " + e.message);
      err.isNetworkError = true;
      throw err;
    }
    throw e;
  }
}

const qs = (o) =>
  new URLSearchParams(Object.entries(o).filter(([, v]) => v !== "" && v != null)).toString();

export const api = {
  categories: () => req("/categories"),
  months: () => req("/months"),
  expenses: (p) => req("/expenses?" + qs(p)),
  create: (b) => req("/expenses", { method: "POST", body: b }),
  update: (id, b) => req(`/expenses/${id}`, { method: "PATCH", body: b }),
  remove: (id) => req(`/expenses/${id}`, { method: "DELETE" }),
  summary: (month) => req("/summary?" + qs({ month })),
  setBudget: (b) => req("/budgets", { method: "PUT", body: b }),
  pending: () => req("/sync/pending"),
  compareStatus: () => req("/compare/status"),
  compareRun: (sizes) => req("/compare/run?sizes=" + sizes.join(","), { method: "POST" }, 0, 300000),
};
