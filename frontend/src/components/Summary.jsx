import { useState } from "react";
import { inr } from "../format.js";

export default function Summary({ summary, onBudget }) {
  const [editing, setEditing] = useState(null);
  const [val, setVal] = useState("");
  if (!summary) return null;
  const commit = async (category) => {
    const n = parseFloat(val);
    setEditing(null);
    if (n > 0) await onBudget({ category, limit_amt: n });
  };
  return (
    <section className="card">
      <div className="sum-head"><h2>{summary.month} overview</h2><strong>{inr(summary.total)} spent</strong></div>
      <div className="cats">
        {summary.categories.map((c) => {
          const pct = c.budget ? Math.min(100, (c.spent / c.budget) * 100) : 0;
          return (
            <div key={c.category} className={"cat" + (c.over_budget ? " over" : "")}>
              <div className="cat-top"><span>{c.category}</span><span>{inr(c.spent)}</span></div>
              <div className="bar"><div style={{ width: pct + "%" }} /></div>
              <div className="cat-bot">
                {editing === c.category ? (
                  <input autoFocus type="number" min="1" value={val} onChange={(e) => setVal(e.target.value)}
                    onBlur={() => commit(c.category)} onKeyDown={(e) => e.key === "Enter" && e.target.blur()} />
                ) : (
                  <button className="link" onClick={() => { setEditing(c.category); setVal(c.budget ?? ""); }}>
                    {c.budget ? `Budget ${inr(c.budget)}` : "Set budget"}
                  </button>
                )}
                {c.over_budget && <span className="badge">Over budget</span>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
