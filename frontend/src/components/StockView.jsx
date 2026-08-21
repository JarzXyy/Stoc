import { useEffect, useState } from "react";
import axios from "axios";
import { PackagePlus, Plus, Search, X } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const StockView = () => {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState("");
  const [amounts, setAmounts] = useState({});
  const [saving, setSaving] = useState(null);
  const emptyProduct = { name: "", category: "", unit: "unit", stock: "", reorder_level: 5, cost_price: "", selling_price: "" };
  const [showAdd, setShowAdd] = useState(false);
  const [newProduct, setNewProduct] = useState(emptyProduct);

  const setNP = (key) => (e) => setNewProduct({ ...newProduct, [key]: e.target.value });
  const submitProduct = async (e) => {
    e.preventDefault();
    if (!newProduct.name.trim() || !newProduct.category.trim()) return toast.error("Name and category are required");
    try {
      await axios.post(`${API}/products`, {
        ...newProduct,
        name: newProduct.name.trim(),
        category: newProduct.category.trim(),
        stock: Number(newProduct.stock) || 0,
        reorder_level: Number(newProduct.reorder_level) || 0,
        cost_price: Number(newProduct.cost_price) || 0,
        selling_price: Number(newProduct.selling_price) || 0,
      });
      toast.success(`${newProduct.name.trim()} added to your store`);
      setShowAdd(false);
      setNewProduct(emptyProduct);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not add the product");
    }
  };

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
        <div className="stock-head-actions">
          <div className="search filter-search">
            <Search size={16} />
            <input data-testid="stock-search-input" placeholder="Search products" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <button className="btn primary" data-testid="add-product-button" onClick={() => setShowAdd(true)}><Plus size={16} /> Add product</button>
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
      {showAdd && (
        <div className="modal-backdrop" data-testid="add-product-modal">
          <form className="modal" onSubmit={submitProduct}>
            <div className="modal-head">
              <div>
                <p className="eyebrow green">NEW PRODUCT</p>
                <h3>Add an item to your store</h3>
              </div>
              <button type="button" className="icon-button" data-testid="close-add-product-modal" onClick={() => setShowAdd(false)}><X size={18} /></button>
            </div>
            <div className="form-row">
              <label>Product name<input data-testid="new-product-name-input" placeholder="e.g. Instant Noodles" value={newProduct.name} onChange={setNP("name")} /></label>
              <label>Category<input data-testid="new-product-category-input" placeholder="e.g. Pantry" value={newProduct.category} onChange={setNP("category")} /></label>
            </div>
            <div className="form-row">
              <label>Unit<input data-testid="new-product-unit-input" placeholder="e.g. pack, kg, bottle" value={newProduct.unit} onChange={setNP("unit")} /></label>
              <label>Starting stock<input data-testid="new-product-stock-input" type="number" min="0" placeholder="0" value={newProduct.stock} onChange={setNP("stock")} /></label>
            </div>
            <div className="form-row">
              <label>Cost price (Rp)<input data-testid="new-product-cost-input" type="number" min="0" placeholder="e.g. 3000" value={newProduct.cost_price} onChange={setNP("cost_price")} /></label>
              <label>Selling price (Rp)<input data-testid="new-product-price-input" type="number" min="0" placeholder="e.g. 4500" value={newProduct.selling_price} onChange={setNP("selling_price")} /></label>
            </div>
            <label>Low-stock alert level<input data-testid="new-product-reorder-input" type="number" min="0" value={newProduct.reorder_level} onChange={setNP("reorder_level")} /></label>
            <button className="btn primary full" data-testid="submit-new-product-button" type="submit"><Plus size={16} /> Save product</button>
          </form>
        </div>
      )}
    </section>
  );
};
