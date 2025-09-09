# scripts/import_products.py
import csv
from decimal import Decimal, InvalidOperation
from typing import Dict, List
import os
from sqlalchemy.exc import SQLAlchemyError

from backend.db.database import sessionLocal   # use your project's session factory
from backend.db import models                   # models.py as you shared

CSV_PATH = "products_master.csv"
BATCH_SIZE = 100  

def parse_decimal(val):
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None

def split_images(s: str) -> List[str]:
    if not s:
        return []
    # accept '|' or ';' separated lists
    if '|' in s:
        parts = s.split('|')
    elif ';' in s:
        parts = s.split(';')
    else:
        parts = [s]
    return [p.strip() for p in parts if p.strip()]

def get_or_create_lookup(cache: Dict, session, Model, lookup_field: str, value: str, **kwargs):
    """
    Generic get_or_create that also caches results to minimize DB calls.
    lookup_field: the model attribute to query by (e.g., 'label' or 'slug' or 'name')
    """
    if not value:
        return None
    key = (Model.__tablename__, lookup_field, value)
    if key in cache:
        return cache[key]
    q = {lookup_field: value}
    instance = session.query(Model).filter_by(**q).first()
    if instance:
        cache[key] = instance
        return instance
    # build create kwargs
    create_kwargs = {lookup_field: value}
    create_kwargs.update(kwargs)
    instance = Model(**create_kwargs)
    session.add(instance)
    session.flush()  # to populate id
    cache[key] = instance
    return instance

def import_csv(path):
    session = sessionLocal()
    cache = {}  # caching lookups to avoid repetitive DB hits
    processed = 0
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed += 1
                # Basic normalization
                product_name = row.get("product_name", "").strip()
                description = row.get("description", "").strip() or None
                category_name = row.get("category_name", "").strip()
                category_slug = row.get("category_slug", (category_name or "").lower().replace(" ", "-"))
                parent_category_name = row.get("parent_category", "").strip() or None
                gender_label = row.get("gender_label", "").strip()
                sku = row.get("variant_sku", "").strip()
                price = parse_decimal(row.get("price", ""))
                sale_price = parse_decimal(row.get("sale_price", ""))
                color_name = row.get("color_name", "").strip()
                color_slug = row.get("color_slug", (color_name or "").lower().replace(" ", "-"))
                size_name = row.get("size_name", "").strip()
                size_slug = row.get("size_slug", (size_name or "").lower().replace(" ", "-"))
                size_order = row.get("size_order") or None
                if size_order:
                    try:
                        size_order = int(size_order)
                    except:
                        size_order = None
                stock_quantity = row.get("stock_quantity") or 0
                try:
                    stock_quantity = int(stock_quantity)
                except:
                    stock_quantity = 0
                dimensions = row.get("dimensions", "").strip() or None
                image_urls_raw = row.get("image_urls", "").strip()
                image_urls = split_images(image_urls_raw)

                # 1) gender
                gender = get_or_create_lookup(cache, session, models.Gender, "label", gender_label)

                # 2) category (handle parent)
                parent_cat = None
                if parent_category_name:
                    parent_cat = get_or_create_lookup(cache, session, models.Category, "name", parent_category_name, slug=(parent_category_name.lower().replace(" ", "-")))
                category = cache.get(("categories", "name", category_name))
                if not category:
                    # try find by slug first
                    category = session.query(models.Category).filter_by(slug=category_slug).first()
                    if not category:
                        category = models.Category(name=category_name, slug=category_slug, parent_id=(parent_cat.id if parent_cat else None))
                        session.add(category)
                        session.flush()
                    cache[("categories", "name", category_name)] = category

                # 3) color & size
                color = get_or_create_lookup(cache, session, models.Color, "name", color_name, slug=color_slug)
                size = get_or_create_lookup(cache, session, models.Size, "name", size_name, slug=size_slug, sort_order=size_order)

                # 4) product (one per product_name)
                prod_key = ("products", "name", product_name)
                product = cache.get(prod_key)
                if not product:
                    product = session.query(models.Product).filter_by(name=product_name).first()
                    if not product:
                        product = models.Product(
                            name=product_name,
                            description=description,
                            category_id=(category.id if category else None),
                            gender_id=(gender.id if gender else None)
                        )
                        session.add(product)
                        session.flush()
                    cache[prod_key] = product

                # 5) variant: check SKU uniqueness. If exists update; else create.
                variant = session.query(models.ProductVariant).filter_by(sku=sku).first()
                if variant:
                    # update fields - keep some existing if missing
                    updated = False
                    if price is not None and variant.price != price:
                        variant.price = price; updated = True
                    if sale_price is not None and variant.sale_price != sale_price:
                        variant.sale_price = sale_price; updated = True
                    if color and variant.color_id != color.id:
                        variant.color_id = color.id; updated = True
                    if size and variant.size_id != size.id:
                        variant.size_id = size.id; updated = True
                    if variant.in_stock != stock_quantity:
                        variant.in_stock = stock_quantity; updated = True
                    if dimensions and variant.dimensions != dimensions:
                        variant.dimensions = dimensions; updated = True
                    if updated:
                        session.add(variant)
                else:
                    variant = models.ProductVariant(
                        product_id=product.id,
                        sku=sku,
                        price=(price if price is not None else Decimal("0.00")),
                        sale_price=sale_price,
                        color_id=(color.id if color else None),
                        size_id=(size.id if size else None),
                        in_stock=stock_quantity,
                        dimensions=dimensions
                    )
                    session.add(variant)
                    session.flush()

                # 6) images
                for img_url in image_urls:
                    # Avoid adding an image duplicate for the same variant/product url combo
                    exists = session.query(models.ProductImage).filter_by(url=img_url, variant_id=variant.id, product_id=product.id).first()
                    if not exists:
                        img = models.ProductImage(product_id=product.id, variant_id=variant.id, url=img_url)
                        session.add(img)

                # commit per batch
                if processed % BATCH_SIZE == 0:
                    session.commit()
                    print(f"Committed {processed} rows")

            # final commit
            session.commit()
            print("CSV import finished. Total rows:", processed)
    except SQLAlchemyError as e:
        session.rollback()
        print("DB error:", e)
        raise
    except Exception as e:
        print("Error reading CSV:", e)
        raise
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH
    if not os.path.exists(path):
        print("CSV file not found:", path)
        sys.exit(1)
    import_csv(path)
