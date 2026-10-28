import { inr } from "../format.js";

export default function ExpenseTable({ items, onEdit, onDelete }) {
  if (!items.length) return <p className="muted">No expenses match.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Date</th><th>Category</th><th>Note</th><th className="num">Amount</th><th /></tr></thead>
        <tbody>
          {items.map((e) => (
            <tr key={e.expense_id}>
              <td>{e.spent_on}</td>
              <td><span className="tag">{e.category}</span></td>
              <td>{e.note}</td>
              <td className="num">{inr(e.amount)}</td>
              <td className="actions">
                <button onClick={() => onEdit(e)}>Edit</button>
                <button className="danger" onClick={() => onDelete(e)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
