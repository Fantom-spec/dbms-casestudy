import { useState } from "react";

export default function ExpenseForm({ categories, initial, onSubmit, onCancel }) {
  const [f, setF] = useState({
    amount: initial?.amount ?? "",
    category: initial?.category ?? "",
    spent_on: initial?.spent_on ?? new Date().toISOString().slice(0, 10),
    note: initial?.note ?? "",
  });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    const ok = await onSubmit({ ...f, amount: parseFloat(f.amount), category: f.category || categories[0] }, initial?.expense_id);
    if (ok && !initial) setF({ ...f, amount: "", note: "" });
  };
  return (
    <form onSubmit={submit} className="form">
      <label>Amount<input type="number" step="0.01" min="0.01" required value={f.amount} onChange={set("amount")} /></label>
      <label>Category
        <select value={f.category || categories[0] || ""} onChange={set("category")}>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label>Date<input type="date" required value={f.spent_on} onChange={set("spent_on")} /></label>
      <label>Note<input value={f.note} onChange={set("note")} placeholder="optional" /></label>
      <div className="row">
        <button className="primary" type="submit">{initial ? "Save changes" : "Add expense"}</button>
        {initial && <button type="button" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}
