from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    unit: str = "unit"
    stock: int = 0
    reorder_level: int = 5
    cost_price: float = 0
    selling_price: float = 0

class ProductCreate(BaseModel):
    name: str
    category: str
    unit: str = "unit"
    stock: int = 0
    reorder_level: int = 5
    cost_price: float = 0
    selling_price: float = 0

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["sale", "purchase"]
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total: float
    note: str = ""
    proof_image: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TransactionCreate(BaseModel):
    type: Literal["sale", "purchase"]
    product_id: str
    quantity: int
    unit_price: float
    note: str = ""
    proof_image: Optional[str] = None

class StockAdjust(BaseModel):
    quantity: int

async def seed_products():
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([
            {"id": "prod-milk", "name": "Fresh Milk", "category": "Dairy", "unit": "bottle", "stock": 24, "reorder_level": 8, "cost_price": 12000, "selling_price": 18000},
            {"id": "prod-bread", "name": "Whole Wheat Bread", "category": "Bakery", "unit": "loaf", "stock": 7, "reorder_level": 10, "cost_price": 11000, "selling_price": 22000},
            {"id": "prod-apples", "name": "Red Apples", "category": "Produce", "unit": "kg", "stock": 42, "reorder_level": 12, "cost_price": 20000, "selling_price": 35000},
            {"id": "prod-rice", "name": "Basmati Rice", "category": "Pantry", "unit": "bag", "stock": 15, "reorder_level": 6, "cost_price": 85000, "selling_price": 120000},
            {"id": "prod-eggs", "name": "Farm Eggs", "category": "Dairy", "unit": "dozen", "stock": 5, "reorder_level": 8, "cost_price": 24000, "selling_price": 36000},
        ])

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Grocery stock API"}

@api_router.get("/products", response_model=List[Product])
async def get_products():
    await seed_products()
    return await db.products.find({}, {"_id": 0}).to_list(1000)

@api_router.post("/products", response_model=Product)
async def create_product(input: ProductCreate):
    product = Product(**input.model_dump())
    await db.products.insert_one(product.model_dump())
    return product

@api_router.post("/products/{product_id}/stock", response_model=Product)
async def add_stock(product_id: str, input: StockAdjust):
    if input.quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    await db.products.update_one({"id": product_id}, {"$inc": {"stock": input.quantity}})
    product["stock"] += input.quantity
    return product

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(type: Optional[str] = None, q: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
    def valid_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
        except ValueError:
            raise HTTPException(400, "Dates must be in YYYY-MM-DD format")
    query = {}
    if type in ("sale", "purchase"):
        query["type"] = type
    if q:
        query["product_name"] = {"$regex": q, "$options": "i"}
    date_range = {}
    if date_from:
        date_range["$gte"] = valid_date(date_from)
    if date_to:
        date_range["$lte"] = valid_date(date_to) + "T23:59:59.999999+00:00"
    if date_range:
        query["created_at"] = date_range
    return await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(input: TransactionCreate):
    await seed_products()
    if input.quantity <= 0 or input.unit_price < 0:
        raise HTTPException(400, "Quantity and price must be positive")
    product = await db.products.find_one({"id": input.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    if input.type == "sale" and product["stock"] < input.quantity:
        raise HTTPException(400, f"Only {product['stock']} {product['unit']}s available")
    change = input.quantity if input.type == "purchase" else -input.quantity
    await db.products.update_one({"id": input.product_id}, {"$inc": {"stock": change}})
    transaction = Transaction(product_name=product["name"], total=input.quantity * input.unit_price, **input.model_dump())
    await db.transactions.insert_one(transaction.model_dump())
    return transaction

@api_router.get("/summary")
async def get_summary():
    await seed_products()
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    transactions = await db.transactions.find({}, {"_id": 0}).to_list(1000)
    sales = sum(t["total"] for t in transactions if t["type"] == "sale")
    purchases = sum(t["total"] for t in transactions if t["type"] == "purchase")
    today = datetime.now(timezone.utc).date().isoformat()
    today_sales = [t for t in transactions if t["type"] == "sale" and t["created_at"].startswith(today)]
    return {"products": len(products), "stock_units": sum(p["stock"] for p in products), "sales": sales, "purchases": purchases, "sales_today": sum(t["total"] for t in today_sales), "sales_today_count": len(today_sales), "cash_flow": sales - purchases, "low_stock": sum(1 for p in products if p["stock"] <= p["reorder_level"])}

@api_router.get("/reports/weekly")
async def weekly_report(week_offset: int = 0):
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    txs = await db.transactions.find(
        {"created_at": {"$gte": week_start.isoformat(), "$lte": week_end.isoformat() + "T23:59:59.999999+00:00"}},
        {"_id": 0},
    ).to_list(5000)
    sales = [t for t in txs if t["type"] == "sale"]
    purchases = [t for t in txs if t["type"] == "purchase"]
    sales_total = sum(t["total"] for t in sales)
    purchases_total = sum(t["total"] for t in purchases)
    movement = {}
    for t in txs:
        m = movement.setdefault(t["product_name"], {"name": t["product_name"], "sold": 0, "purchased": 0, "sales_value": 0.0, "purchases_value": 0.0})
        if t["type"] == "sale":
            m["sold"] += t["quantity"]
            m["sales_value"] += t["total"]
        else:
            m["purchased"] += t["quantity"]
            m["purchases_value"] += t["total"]
    products = sorted(movement.values(), key=lambda m: m["sales_value"] + m["purchases_value"], reverse=True)
    label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
    cash_flow = sales_total - purchases_total
    idr = lambda v: "Rp " + f"{v:,.0f}".replace(",", ".")
    lines = [
        f"GreenBasket weekly report ({label})",
        f"Sales: {idr(sales_total)} ({len(sales)} transactions)",
        f"Purchases: {idr(purchases_total)} ({len(purchases)} transactions)",
        f"Cash flow: {'+' if cash_flow >= 0 else '-'}{idr(abs(cash_flow))}",
    ]
    if products:
        lines.append("Stock movement:")
        for m in products:
            lines.append(f"- {m['name']}: {m['sold']} sold, {m['purchased']} purchased")
    else:
        lines.append("No stock movement this week.")
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "label": label,
        "sales_total": sales_total,
        "purchases_total": purchases_total,
        "cash_flow": cash_flow,
        "sales_count": len(sales),
        "purchases_count": len(purchases),
        "products": products,
        "share_text": "\n".join(lines),
    }

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()