import { useEffect, useState } from "react";
import axios from "axios";
import { ArrowDownLeft, ArrowUpRight, Image as ImageIcon, Search, X } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const money = (n) => `Rp ${Number(n || 0).toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;

export const HistoryView = () => {
  const [transactions, setTransactions] = useState([]);
  const [filters, setFilters] = useState({ type: "", q: "", date_from: "", date_to: "" });
  const [proof, setProof] = useState(null);
  const [proofError, setProofError] = useState(false);

  useEffect(() => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    const t = setTimeout(() => {
      axios.get(`${API}/transactions`, { params }).then((r) => setTransactions(r.data)).catch(() => toast.error("Could not load transactions"));
    }, 250);
    return () => clearTimeout(t);
  }, [filters]);

  const set = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });

  return (
    <section className="content">
      <div className="intro">
        <div>
          <p className="eyebrow green">TRANSACTION HISTORY</p>
          <h2>Every sale and purchase, in one place.</h2>
          <p className="subcopy">Search by product, filter by type or date, and open saved payment proofs.</p>
        </div>
      </div>
      <div className="filter-bar" data-testid="history-filter-bar">
        <div className="search filter-search">
          <Search size={16} />
          <input data-testid="history-search-input" placeholder="Search products" value={filters.q} onChange={set("q")} />
        </div>
        <select data-testid="history-type-filter" className="filter-select" value={filters.type} onChange={set("type")}>
          <option value="">All movements</option>
          <option value="sale">Sales only</option>
          <option value="purchase">Purchases only</option>
        </select>
        <label className="filter-date">From<input data-testid="history-date-from" type="date" value={filters.date_from} onChange={set("date_from")} /></label>
        <label className="filter-date">To<input data-testid="history-date-to" type="date" value={filters.date_to} onChange={set("date_to")} /></label>
        {(filters.q || filters.type || filters.date_from || filters.date_to) && (
          <button className="btn secondary" data-testid="history-clear-filters" onClick={() => setFilters({ type: "", q: "", date_from: "", date_to: "" })}>Clear</button>
        )}
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>DATE</th><th>TYPE</th><th>PRODUCT</th><th>QTY</th><th>UNIT PRICE</th><th>TOTAL</th><th>NOTE</th><th>PROOF</th></tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id} data-testid="history-row">
                  <td>{new Date(t.created_at).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}</td>
                  <td><span className={`type-badge ${t.type}`}>{t.type === "sale" ? <ArrowUpRight size={12} /> : <ArrowDownLeft size={12} />}{t.type}</span></td>
                  <td><b>{t.product_name}</b></td>
                  <td>{t.quantity}</td>
                  <td>{money(t.unit_price)}</td>
                  <td><strong className={t.type === "sale" ? "positive" : "negative"}>{t.type === "sale" ? "+" : "−"}{money(t.total)}</strong></td>
                  <td className="note-cell">{t.note || <span className="muted">—</span>}</td>
                  <td>
                    {t.proof_image ? (
                      <button className="proof-thumb" data-testid="view-proof-button" onClick={() => { setProofError(false); setProof(t); }}>
                        <img src={t.proof_image} alt="Payment proof" onError={(e) => { e.currentTarget.style.display = "none"; e.currentTarget.parentElement.classList.add("broken"); }} />
                      </button>
                    ) : (
                      <span className="no-proof"><ImageIcon size={14} /></span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!transactions.length && <div className="empty" data-testid="history-empty">No transactions match these filters.</div>}
        </div>
      </section>
      {proof && (
        <div className="modal-backdrop" data-testid="proof-modal" onClick={() => setProof(null)}>
          <div className="modal proof-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="eyebrow green">PAYMENT PROOF</p>
                <h3>{proof.product_name}</h3>
                <p className="subcopy">{proof.type} · {proof.quantity} units · {money(proof.total)} · {new Date(proof.created_at).toLocaleDateString()}</p>
              </div>
              <button type="button" className="icon-button" data-testid="close-proof-modal" onClick={() => setProof(null)}><X size={18} /></button>
            </div>
            {proofError ? (
              <div className="empty" data-testid="proof-image-error">This image could not be displayed.</div>
            ) : (
              <img className="proof-full" src={proof.proof_image} alt="Payment proof full view" onError={() => setProofError(true)} />
            )}
          </div>
        </div>
      )}
    </section>
  );
};
