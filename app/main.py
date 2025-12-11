from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Product
from .scraping import scrape_product

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def read_root(
    request: Request,
    db: Session = Depends(get_db),
    category: str | None = None,
    entry_type: str | None = None,
    q: str | None = None,
):
    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category)

    if entry_type:
        query = query.filter(Product.entry_type == entry_type)

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            (Product.title.ilike(pattern)) | (Product.notes.ilike(pattern))
        )

    products = query.order_by(Product.purchased, Product.created_at.desc()).all()

    # Llista de categories existents per al dropdown
    raw_categories = db.query(Product.category).distinct().all()
    categories = sorted(
        {c[0] for c in raw_categories if c[0] is not None and c[0] != ""}
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "current_category": category or "",
            "current_entry_type": entry_type or "",
            "current_q": q or "",
        },
    )

@app.post("/add")
def add_product(
    request: Request,
    url: str = Form(...),
    notes: str = Form(""),
    entry_type: str = Form("product"),
    category: str = Form(""),
    db: Session = Depends(get_db),
):
    existing = db.query(Product).filter(Product.url == url).first()
    if existing:
        return RedirectResponse(url=f"/product/{existing.id}", status_code=303)

    scraped = scrape_product(url)

    product = Product(
        url=url,
        source=scraped.source,
        title=scraped.title,
        image_url=scraped.image_url,
        price=scraped.price,
        currency=scraped.currency,
        notes=notes or None,
        entry_type=entry_type,
        category=category or None,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return RedirectResponse(url=f"/product/{product.id}", status_code=303)


@app.get("/product/{product_id}")
def product_detail(
    product_id: int, request: Request, db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "product_detail.html", {"request": request, "product": product}
    )

@app.post("/toggle-purchased/{product_id}")
def toggle_purchased(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {"success": False}

    product.purchased = not product.purchased
    db.commit()
    db.refresh(product)
    
    return {"success": True, "purchased": product.purchased}
