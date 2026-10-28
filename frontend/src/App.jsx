import { useState } from "react";
import Tracker from "./pages/Tracker.jsx";
import Compare from "./pages/Compare.jsx";

export default function App() {
  const [tab, setTab] = useState("tracker");
  return (
    <div className="app">
      <nav className="tabs">
        <strong className="brand">Expense Tracker</strong>
        <button className={tab === "tracker" ? "on" : ""} onClick={() => setTab("tracker")}>Expenses</button>
        <button className={tab === "compare" ? "on" : ""} onClick={() => setTab("compare")}>SQLite vs PostgreSQL</button>
      </nav>
      {tab === "tracker" ? <Tracker /> : <Compare />}
    </div>
  );
}
