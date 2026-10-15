from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, String, Integer, Numeric, Date, DateTime, ForeignKey, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./salesia.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

DB_URL = database_url()
engine = create_engine(DB_URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    doc: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), default="Empresa")
    email: Mapped[str] = mapped_column(String(180), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    address: Mapped[str] = mapped_column(String(250), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default="General")
    price: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[int] = mapped_column(Integer, default=1)

class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), default="Factura")
    issue_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    customer: Mapped[Customer] = relationship()
    details: Mapped[list["SaleDetail"]] = relationship(back_populates="sale", cascade="all, delete-orphan")

class SaleDetail(Base):
    __tablename__ = "sale_details"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    sale: Mapped[Sale] = relationship(back_populates="details")
    product: Mapped[Product] = relationship()

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), default="Por definir")
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales.id"), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(String(250), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    details: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CustomerIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    doc: str = Field(min_length=8, max_length=20)
    type: str = "Empresa"
    email: str = ""
    phone: str = ""
    address: str = ""
class CustomerOut(CustomerIn):
    id: int
    model_config = ConfigDict(from_attributes=True)
class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    sku: str = Field(min_length=2, max_length=50)
    category: str = "General"
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0)
class ProductOut(ProductIn):
    id: int
    model_config = ConfigDict(from_attributes=True)
class SaleItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=100000)
class SaleIn(BaseModel):
    customer_id: int
    document_type: str = "Factura"
    issue_date: date = Field(default_factory=date.today)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.18"), ge=0, le=1)
    items: list[SaleItemIn] = Field(min_length=1)
class SaleOut(BaseModel):
    id: str
    customer: str
    date: str
    status: str
    total: float
    items: int

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def money(v): return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def sale_dict(s: Sale):
    return {"id": s.number, "customer": s.customer.name, "date": s.issue_date.strftime("%d %b %Y"), "status": s.status,
            "total": float(s.total), "items": sum(d.quantity for d in s.details)}

def seed(db: Session):
    if db.scalar(select(func.count(Customer.id))) == 0:
        db.add_all([
          Customer(name="Comercial Andina S.A.C.",doc="20604578123",type="Empresa",email="compras@andina.pe",phone="(01) 445-8832",address="Av. Javier Prado 1840, San Isidro, Lima"),
          Customer(name="Inversiones del Pacífico E.I.R.L.",doc="20517893461",type="Empresa",email="administracion@pacifico.pe",phone="(01) 441-7620",address="Av. La Marina 2250, San Miguel, Lima"),
          Customer(name="María Fernanda Torres",doc="46892157",type="Persona",email="maria.torres@email.com",phone="987 654 321",address="Calle Los Olivos 324, Miraflores, Lima"),
          Customer(name="Grupo Horizonte Perú S.A.C.",doc="20608912456",type="Empresa",email="contacto@horizonte.pe",phone="(01) 505-1290",address="Jr. Las Begonias 475, Surco, Lima")])
    if db.scalar(select(func.count(Product.id))) == 0:
        db.add_all([Product(name="Laptop empresarial Pro 14",sku="TEC-001",category="Tecnología",price=3299,stock=24),Product(name="Monitor profesional 27”",sku="TEC-002",category="Tecnología",price=899,stock=18),Product(name="Silla ergonómica ejecutiva",sku="MOB-014",category="Mobiliario",price=749,stock=7),Product(name="Teclado inalámbrico Business",sku="ACC-021",category="Accesorios",price=149,stock=62),Product(name="Estación de acoplamiento USB-C",sku="TEC-031",category="Tecnología",price=429,stock=3)])
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    yield

app = FastAPI(title="SalesIA Enterprise API", version="1.0.0", description="API para ventas, clientes, productos, inventario y analítica.", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins + (["https://*.vercel.app"] if "*" in origins else []), allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"), allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root(): return {"name":"SalesIA Enterprise API", "status":"ok", "docs":"/docs"}
@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1)); return {"status":"healthy", "database":"connected"}
@app.get("/customers", response_model=list[CustomerOut])
def customers(q: str = Query(default="", max_length=100), db: Session = Depends(get_db)):
    stmt = select(Customer).where((Customer.name.ilike(f"%{q}%")) | (Customer.doc.ilike(f"%{q}%")) | (Customer.email.ilike(f"%{q}%"))).order_by(Customer.name)
    return db.scalars(stmt).all()
@app.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerIn, db: Session = Depends(get_db)):
    if db.scalar(select(Customer).where(Customer.doc == payload.doc)): raise HTTPException(409, "Ya existe un cliente con ese documento.")
    obj = Customer(**payload.model_dump()); db.add(obj); db.flush(); db.add(AuditLog(action="create",entity="customer",entity_id=str(obj.id),details=obj.name)); db.commit(); db.refresh(obj); return obj
@app.get("/products", response_model=list[ProductOut])
def products(q: str = Query(default="", max_length=100), db: Session = Depends(get_db)):
    return db.scalars(select(Product).where(Product.active == 1, (Product.name.ilike(f"%{q}%")) | (Product.sku.ilike(f"%{q}%")) | (Product.category.ilike(f"%{q}%"))).order_by(Product.name)).all()
@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.sku == payload.sku)): raise HTTPException(409, "Ya existe un producto con ese SKU.")
    obj = Product(**payload.model_dump()); db.add(obj); db.flush(); db.add(AuditLog(action="create",entity="product",entity_id=str(obj.id),details=obj.name)); db.commit(); db.refresh(obj); return obj
@app.get("/sales")
def sales(q: str = Query(default="", max_length=100), db: Session = Depends(get_db)):
    stmt = select(Sale).join(Customer).where((Sale.number.ilike(f"%{q}%")) | (Customer.name.ilike(f"%{q}%")) | (Sale.status.ilike(f"%{q}%"))).order_by(Sale.created_at.desc())
    return [sale_dict(s) for s in db.scalars(stmt).unique().all()]
@app.post("/sales", status_code=201)
def create_sale(payload: SaleIn, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if not customer: raise HTTPException(404, "Cliente no encontrado.")
    if payload.discount < 0: raise HTTPException(422, "El descuento no puede ser negativo.")
    try:
        resolved=[]; subtotal=Decimal("0.00")
        for item in payload.items:
            product=db.get(Product,item.product_id)
            if not product or not product.active: raise HTTPException(404, f"Producto {item.product_id} no encontrado.")
            if product.stock < item.quantity: raise HTTPException(409, f"Stock insuficiente para {product.name}. Disponible: {product.stock}.")
            line=money(product.price*item.quantity); subtotal += line; resolved.append((product,item.quantity,line))
        subtotal=money(subtotal)
        if payload.discount > subtotal: raise HTTPException(422, "El descuento supera el subtotal.")
        taxable=money(subtotal-payload.discount); tax=money(taxable*payload.tax_rate); total=money(taxable+tax)
        last=db.scalar(select(func.count(Sale.id))) or 0
        number=f"VTA-{date.today().year}-{last+1:05d}"
        while db.scalar(select(Sale.id).where(Sale.number==number)):
            last += 1; number=f"VTA-{date.today().year}-{last+1:05d}"
        sale=Sale(number=number,customer_id=customer.id,document_type=payload.document_type,issue_date=payload.issue_date,status="Pendiente",subtotal=subtotal,discount=payload.discount,tax=tax,total=total)
        db.add(sale); db.flush()
        for product,qty,line in resolved:
            product.stock -= qty
            db.add(SaleDetail(sale_id=sale.id,product_id=product.id,quantity=qty,unit_price=product.price,line_total=line))
            db.add(InventoryMovement(product_id=product.id,sale_id=sale.id,movement_type="SALIDA",quantity=qty,note=f"Venta {number}"))
        db.add(Payment(sale_id=sale.id,amount=total,method="Por definir",status="Pendiente"))
        db.add(AuditLog(action="create",entity="sale",entity_id=number,details=f"Cliente {customer.doc}; total {total}"))
        db.commit(); db.refresh(sale); return sale_dict(sale)
    except Exception:
        db.rollback(); raise
@app.patch("/sales/{sale_number}/status")
def update_sale_status(sale_number: str, payload: dict, db: Session = Depends(get_db)):
    new_status = str(payload.get("status", "")).strip()
    allowed = {"Pendiente", "Pagada", "Anulada"}
    if new_status not in allowed:
        raise HTTPException(422, "Estado no válido. Usa Pendiente, Pagada o Anulada.")
    sale = db.scalar(select(Sale).where(Sale.number == sale_number))
    if not sale:
        raise HTTPException(404, "No se encontró la venta.")
    old_status = sale.status
    if old_status == new_status:
        return sale_dict(sale)
    if old_status == "Anulada":
        raise HTTPException(409, "Una venta anulada no puede reactivarse. Registra una nueva venta.")
    if new_status == "Pagada" and old_status != "Pendiente":
        raise HTTPException(409, "Solo se pueden marcar como pagadas las ventas pendientes.")
    if new_status == "Anulada":
        # Revertir existencias una sola vez al anular la venta.
        for detail in sale.details:
            product = db.get(Product, detail.product_id)
            if product:
                product.stock += detail.quantity
                db.add(InventoryMovement(product_id=product.id, sale_id=sale.id,
                    movement_type="ENTRADA", quantity=detail.quantity,
                    note=f"Reversión por anulación de {sale.number}"))
        for payment in db.scalars(select(Payment).where(Payment.sale_id == sale.id)).all():
            payment.status = "Anulado"
    else:
        for payment in db.scalars(select(Payment).where(Payment.sale_id == sale.id)).all():
            payment.status = "Pagado"
            payment.paid_at = datetime.utcnow()
    sale.status = new_status
    db.add(AuditLog(action="status_change", entity="sale", entity_id=sale.number,
                    details=f"{old_status} -> {new_status}"))
    db.commit()
    db.refresh(sale)
    return sale_dict(sale)

@app.get("/inventory/movements")
def inventory_movements(db: Session = Depends(get_db)):
    rows=db.execute(select(InventoryMovement,Product.name,Product.sku).join(Product).order_by(InventoryMovement.created_at.desc()).limit(250)).all()
    return [{"id":m.id,"product":name,"sku":sku,"type":m.movement_type,"quantity":m.quantity,"sale_id":m.sale_id,"note":m.note,"created_at":m.created_at.isoformat()} for m,name,sku in rows]
@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    sales_list=db.scalars(select(Sale)).all(); products_list=db.scalars(select(Product).where(Product.active==1)).all()
    paid=sum((s.total for s in sales_list if s.status=="Pagada"),Decimal(0)); total=sum((s.total for s in sales_list),Decimal(0))
    return {"sales_count":len(sales_list),"revenue":float(total),"paid_revenue":float(paid),"customers_count":db.scalar(select(func.count(Customer.id))) or 0,"products_count":len(products_list),"stock_units":sum(p.stock for p in products_list),"pending_count":sum(1 for s in sales_list if s.status=="Pendiente"),"sales": [sale_dict(s) for s in sorted(sales_list,key=lambda x:x.created_at,reverse=True)[:10]]}
@app.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    vals=[float(s.total) for s in db.scalars(select(Sale)).all()]; ordered=sorted(vals); n=len(vals)
    mean=sum(vals)/n if n else 0
    median=(ordered[n//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2) if n else 0
    return {"transactions":n,"revenue":round(sum(vals),2),"mean":round(mean,2),"median":round(median,2),"min":min(vals) if vals else 0,"max":max(vals) if vals else 0,"variable":"Monto total por venta","unit":"PEN"}
@app.post("/probability/bayes")
def bayes(payload: dict):
    try:
        prior=float(payload.get("prior",30))/100; likelihood=float(payload.get("likelihood",70))/100; false_positive=float(payload.get("false_positive",15))/100
        if any(x<0 or x>1 for x in (prior,likelihood,false_positive)): raise ValueError()
        numerator=prior*likelihood; denominator=numerator+(1-prior)*false_positive
        if denominator == 0: raise HTTPException(422,"No se puede calcular con estos valores: P(B) es cero.")
        return {"posterior":round(numerator/denominator*100,4),"prior":prior*100,"likelihood":likelihood*100,"false_positive":false_positive*100}
    except (TypeError,ValueError): raise HTTPException(422,"Envía prior, likelihood y false_positive como porcentajes entre 0 y 100.")
@app.get("/insights")
def insights(db: Session = Depends(get_db)):
    total=db.scalar(select(func.count(Sale.id))) or 0; pending=db.scalar(select(func.count(Sale.id)).where(Sale.status=="Pendiente")) or 0
    low=db.scalars(select(Product).where(Product.active==1,Product.stock<5).order_by(Product.stock)).all()
    items=[]
    if pending: items.append({"title":"Ventas pendientes de pago","description":f"Hay {pending} ventas pendientes que requieren seguimiento.","type":"attention","evidence":{"pending_sales":pending}})
    if low: items.append({"title":"Stock bajo","description":f"{len(low)} productos tienen menos de 5 unidades.","type":"warning","evidence":{"products":[p.sku for p in low]}})
    if total and not items: items.append({"title":"Operación registrada","description":f"Se han registrado {total} ventas. Continúa monitoreando la evolución comercial.","type":"info","evidence":{"sales_count":total}})
    return items
@app.get("/reports/sales.csv")
def sales_csv(db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    import csv, io
    buffer=io.StringIO(); writer=csv.writer(buffer); writer.writerow(["numero","fecha","cliente","documento","estado","subtotal","descuento","igv","total","unidades"])
    for s in db.scalars(select(Sale).join(Customer).order_by(Sale.created_at.desc())).unique().all():
        writer.writerow([s.number,s.issue_date.isoformat(),s.customer.name,s.customer.doc,s.status,str(s.subtotal),str(s.discount),str(s.tax),str(s.total),sum(d.quantity for d in s.details)])
    from fastapi.responses import Response
    return Response(content="\ufeff"+buffer.getvalue(),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=salesia-ventas.csv"})
@app.get("/audit")
def audit(db: Session = Depends(get_db)):
    rows=db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return [{"id":x.id,"action":x.action,"entity":x.entity,"entity_id":x.entity_id,"details":x.details,"created_at":x.created_at.isoformat()} for x in rows]
