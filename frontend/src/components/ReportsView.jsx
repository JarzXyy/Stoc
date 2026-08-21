import { useEffect, useState } from "react";
import axios from "axios";
import { ChevronLeft, ChevronRight, Copy } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const money = (n) => `Rp ${Number(n || 0).toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;

export const ReportsView = () => {
  const [offset, setOffset] = useState(0);
  const [report, setReport] = useState(null);

  useEffect(() => {
    axios.get(`${API}/reports/weekly`, { params: { week_offset: offset } }).then((r) => setReport(r.data)).catch(() => toast.error("Could not load the report"));
  }, [offset]);

  const copyReport = async () => {
    try {
      await navigator.clipboard.writeText(report.share_text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = report.share_text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    toast.success("Report copied — paste it anywhere");
  };

  if (!report) return <section className="content"><div className="empty">Loading report…</div></section>;

  return (
    <section className="content">
      <div className="intro">
        <div>
          <p className="eyebrow green">WEEKLY REPORT</p>
          <h2>Your week, summed up.</h2>
          <p className="subcopy">Cash flow and stock movement for the selected week, ready to share.</p>
        </div>
        <button className="btn primary" data-testid="copy-report-button" onClick={copyReport}><Copy size={16} /> Copy summary</button>
      </div>
      <div className="week-nav">
        <button className="icon-button week-arrow" data-testid="prev-week-button" onClick={() => setOffset(offset - 1)}><ChevronLeft size={18} /></button>
        <span className="week-label" data-testid="week-label">{report.label}{offset === 0 && <em> · this week</em>}</span>
        <button className="icon-button week-arrow" data-testid="next-week-button" disabled={offset === 0} onClick={() => setOffset(offset + 1)}><ChevronRight size={18} /></button>
      </div>
      <div className="stat-grid report-grid">
        <div className="stat-card"><div className="stat-label">SALES</div><strong data-testid="report-sales-total">{money(report.sales_total)}</strong><span className="stat-note">{report.sales_count} transactions</span></div>
        <div className="stat-card"><div className="stat-label">PURCHASES</div><strong data-testid="report-purchases-total">{money(report.purchases_total)}</strong><span className="stat-note">{report.purchases_count} transactions</span></div>
        <div className="stat-card"><div className="stat-label">CASH FLOW</div><strong data-testid="report-cash-flow" className={report.cash_flow < 0 ? "negative" : "positive"}>{report.cash_flow < 0 ? "−" : "+"}{money(Math.abs(report.cash_flow))}</strong><span className="stat-note">Sales less purchases</span></div>
      </div>
      <section className="panel">
        <div className="panel-head"><div><h3>Stock movement</h3><p>Units in and out per product this week</p></div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>PRODUCT</th><th>SOLD</th><th>PURCHASED</th><th>SALES VALUE</th><th>PURCHASE VALUE</th></tr></thead>
            <tbody>
              {report.products.map((m) => (
                <tr key={m.name} data-testid="report-product-row">
                  <td><b>{m.name}</b></td>
                  <td>{m.sold} <span className="muted">units</span></td>
                  <td>{m.purchased} <span className="muted">units</span></td>
                  <td><span className="positive">{money(m.sales_value)}</span></td>
                  <td>{money(m.purchases_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!report.products.length && <div className="empty" data-testid="report-empty">No stock movement recorded this week.</div>}
        </div>
      </section>
      <section className="panel share-preview">
        <div className="panel-head"><div><h3>Share preview</h3><p>Exactly what gets copied</p></div></div>
        <pre className="share-text" data-testid="report-share-text">{report.share_text}</pre>
      </section>
    </section>
  );
};
