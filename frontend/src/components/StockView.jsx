import { useEffect, useState } from "react";
import axios from "axios";
import { PackagePlus, Search } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const StockView = () => {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState("");
  const [amounts, setAmounts] = useState({});
  const [saving, setSaving] = useState(null);

  const load = () => axios.get(`${API}/products`).then((r) => setProducts(r.data)).catch(() => toast.error("Could not load products"));
  useEffect(() => { load(); }, []);

  const filtered = products.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()) || p.category.toLowerCase().includes(query.toLowerCase()));

  const addStock = async (p) => {
    const qty = Number(amounts[p.id]);
    if (!qty || qty <= 0) return toast.error("Enter how many units to add");
    setSaving(p.id);
    try {
      await axios.post(`${API}/products/${p.id}/stock`, { quantity: qty });
      toast.success(`Added ${qty} ${p.unit}s to ${p.name}`);
      setAmounts({ ...amounts, [p.id]: "" });
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not update stock");
    }
    setSaving(null);
  };

  return (
    <section className="content">
      <div className="intro">
        <div>
          <p className="eyebrow green">STOCK CONTROL</p>
          <h2>Top up your shelves.</h2>
          <p className="subcopy">Add units to any product — stock updates instantly across the store.</p>
        </div>
        <div className="search filter-search">
          <Search size={16} />
          <input data-testid="stock-search-input" placeholder="Search products" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>PRODUCT</th><th>CATEGORY</th><th>IN STOCK</th><th>STATUS</th><th>ADD UNITS</th><th></th></tr></thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} data-testid="stock-row">
                  <td><div className="product-name"><span className="product-letter">{p.name[0]}</span><span>{p.name}<small>per {p.unit}</small></span></div></td>
                  <td><span className="category">{p.category}</span></td>
                  <td><b data-testid={`stock-level-${p.id}`}>{p.stock}</b> <span className="muted">{p.unit}s</span></td>
                  <td><span className={`stock-status ${p.stock <= p.reorder_level ? "low" : "good"}`}>{p.stock <= p.reorder_level ? "Low stock" : "In stock"}</span></td>
                  <td>
                    <input className="stock-qty-input" data-testid={`stock-qty-input-${p.id}`} type="number" min="1" placeholder="0" value={amounts[p.id] || ""} onChange={(e) => setAmounts({ ...amounts, [p.id]: e.target.value })} />
                  </td>
                  <td>
                    <button className="btn primary small" data-testid={`add-stock-button-${p.id}`} disabled={saving === p.id} onClick={() => addStock(p)}>
                      <PackagePlus size={14} /> {saving === p.id ? "Adding…" : "Add stock"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filtered.length && <div className="empty" data-testid="stock-empty">No products match your search.</div>}
        </div>
      </section>
    </section>
  );
};
