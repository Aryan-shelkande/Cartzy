# CARTZY

**Add everything you need. Compare your entire cart. Shop where you save the most.**

Build one shopping list (choosing the brand for each item), then compare the **final payable amount** for that whole cart on seven quick-commerce platforms: item prices plus delivery, handling, platform and small-cart fees, minus discounts. Per-product price comparison is still available as secondary detail.

> **Demo data.** All prices, availability, fees and discounts are generated mock data for demonstration. They are not live platform prices.

- **Backend:** Django 5 + Django REST Framework, SQLite (`backend/`)
- **Frontend:** React 19 + Vite, plain CSS (`frontend/`)

## Setup

Requirements: Python 3.11+, Node 20+.

```bash
# Backend: http://localhost:8000
cd backend
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data          # 92 products, 7 platforms, 5 Pune locations, mock prices and fees
python manage.py runserver

# Frontend: http://localhost:5173 (in a second terminal)
cd frontend
npm install
npm run dev
```

The frontend calls `http://localhost:8000/api` by default. To change it, copy `frontend/.env.example` to `frontend/.env` and edit `VITE_API_URL`.

## Tests

- Backend: `cd backend && python manage.py test catalog`
- Browser smoke tests (optional): with both dev servers running, `pip install playwright && playwright install chromium`, then `python e2e/ui_smoke.py`. These cover the dashboard, adding items and rapid quantity clicks, the comparison drawer, search and filters, cart comparison across locations (including the fee breakdown on every card), changing brands and accepting alternatives, the confetti milestone and mobile layout.

`seed_data` is idempotent. Re-running it refreshes the catalogue and regenerates the same mock prices.

## Project layout

```
backend/
  cartzy/settings.py            DB, DRF and CORS config (env-driven)
  catalog/models.py             City, Location, Category, Platform, Product, ProductPrice, PlatformCharges, ShoppingList(+Item)
  catalog/services.py           All comparison logic: product offers, brand matching, charges, cart totals
  catalog/views.py, urls.py     REST endpoints: input validation, then call services
  catalog/serializers.py
  catalog/exceptions.py         Consistent {"error": {...}} responses
  catalog/seed/catalog_data.py  Locations, platforms, categories, products
  catalog/seed/mock_prices.py   The only place mock prices and fees are generated
  catalog/management/commands/seed_data.py
  catalog/tests.py
frontend/src/
  api.js                        REST client
  useCart.js, useProducts.js, useCartComparison.js   data hooks
  components/                   Header, Hero, CategoryBar, ProductCard, ProductRail, ProductBrowser,
                                ComparisonDrawer, CartSummary (sidebar list), CartView (compare page),
                                PlatformCartCard, PlatformLogo, ProductImage, Toasts, ...
frontend/public/
  logos/                        Platform logos (Wikimedia Commons, see Image sources)
  images/products/              Product photos as WebP + ATTRIBUTION.md
  confetti.js                   ~60-line canvas confetti, no dependency
  index.css                     Theme tokens + all styles
```

## REST API

All price endpoints require `?location=<slug>`. They also accept `?platforms=zepto,blinkit` to compare a subset of platforms.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/locations/` | Delivery locations |
| GET | `/api/categories/` | Categories with product counts |
| GET | `/api/platforms/` | Active platforms |
| GET | `/api/products/` | Paginated products with price summary (`min_price`, `max_price`, `savings`, `available_count`, `alternatives_count`). Filters: `search` (name, brand, generic name, category), `category`, `available=true/false`, `featured=true`, `ordering=name/price/-price/savings/popular`, `page`, `page_size` (max 60) |
| GET | `/api/products/{id}/compare/` | Every platform's price/availability for one product, cheapest flagged, plus `alternatives` (other brands, same item and size) |
| POST | `/api/carts/` | Create an anonymous shopping list (UUID) |
| GET | `/api/carts/{id}/` | Shopping list items, each with `accept_alternatives` and `brand_options` |
| POST | `/api/carts/{id}/items/` | `{product_id, quantity}`. Adds the product or increments its quantity |
| DELETE | `/api/carts/{id}/items/` | Clear the list |
| PATCH | `/api/carts/{id}/items/{product_id}/` | Any of `{quantity (1–99), accept_alternatives, product_id}`. `product_id` switches to another brand of the same item and size (merging if that brand is already listed) |
| DELETE | `/api/carts/{id}/items/{product_id}/` | Remove the item |
| GET | `/api/carts/{id}/compare/` | Per platform: final payable, charge breakdown, exact / alternative / unavailable counts and item lines. Overall: cheapest and highest complete cart, savings, cheapest exact-brand cart |

Errors always have the shape `{"error": {"status": 400, "message": "...", "details": {...}}}`.

## How comparison works

- **One product record per SKU.** Platform prices are `ProductPrice` rows keyed by (product, platform, location). Product records are never duplicated per platform.
- **Brand alternatives.** Each product has a `generic_name` (e.g. "Salt") and a `match_key` built from generic name + pack size (`salt-1-kg`). Products sharing a `match_key` are alternative brands; different pack sizes never match.
- **Product comparison** lists every active platform. A platform without a listing, or one that is out of stock, is shown as unavailable rather than dropped. The cheapest and highest prices, and the savings between them, use only available offers. Other brands are listed separately.
- **Cart comparison** (`services.compare_cart`) matches every list item on every platform:
  - `exact`: the requested brand is in stock. Always preferred.
  - `alternative_available`: the requested brand isn't, but the cheapest in-stock brand with the same `match_key` is shown. It is **not** counted in the total.
  - `alternative`: as above, after the user ticks "Accept another brand" for that item. Counted, and labelled as another brand.
  - `unavailable`: no brand of that item and size is in stock.
- **Final payable** (`services.calculate_charges`) = item subtotal + delivery fee (waived above the free-delivery threshold) + handling fee + platform fee + small-cart fee (below a minimum) − discount (percentage with a cap and minimum order, rounded to whole rupees). Fees are `PlatformCharges` rows per (platform, location), editable in the Django admin. An empty order costs nothing.
- **Ranking.** A cart is **complete** only when every item is exact or an accepted alternative. Only complete carts are ranked by final payable; on equal totals the one with more exact brands wins. The response flags the cheapest and highest complete carts, the savings between them, how much more each complete cart costs than the cheapest, and the cheapest cart with *only* exact brands. Incomplete carts show a partial amount ("payable for 3 of 5 items"), are listed after complete ones and are never called cheapest. When no cart is complete, the UI says so. There is no split-cart optimisation.
- React only displays these results. It never calculates totals itself.

## Replacing mock data with real data

Only `catalog/seed/mock_prices.py` invents prices and fees. A legitimate source (official API, affiliate feed, merchant partnership, licensed provider) would write the same `ProductPrice` and `PlatformCharges` rows with its own `source` value, for example from a new management command. `services.py`, the API and the frontend need no changes. Unauthorized scraping is out of scope by design.

## Image sources

- **Product photos** (45 of 92 products) are front-of-pack photos from Open Food Facts, Open Beauty Facts and Open Products Facts, licensed CC BY-SA 3.0. Each was checked by hand against the product it illustrates, resized to 360 px WebP (≈12 KB each) and credited, with its barcode and source page, in `frontend/public/images/products/ATTRIBUTION.md`. Some show a different pack size of the same product. Products without a verified photo, or whose photo fails to load, show their emoji tile.
- **Platform logos** come from Wikimedia Commons (public domain, CC0 or CC BY-SA 4.0 as listed there): Zepto, Blinkit, Swiggy 2024 (used for Instamart), Amazon, Flipkart Minutes, BigBasket, JioMart. They are trademarks of their owners and are shown only to identify each platform; Cartzy is not affiliated with them. A missing logo falls back to a coloured initial.

## Switching to MySQL

Settings read the database from the environment. Install `mysqlclient` and set `DB_ENGINE=django.db.backends.mysql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT`. Then run `migrate` and `seed_data`.

## Assumptions

- The 7th platform slot is seeded as **JioMart**. Its name, logo (`logo_url`) and `is_active` flag can be changed in the Django admin.
- `Product.image_url` and `Platform.logo_url` accept an absolute URL or a path under `frontend/public/`.
- MRPs are approximate, and mock prices never exceed MRP. Prices, availability and fees vary per platform and location, deterministically.
- "Accept another brand" is a per-item choice that applies on every platform. When several alternatives are in stock, the cheapest is used.
- There is no login. The shopping list is stored server-side and identified by a UUID kept in the browser's localStorage. A `user` FK can be added when authentication arrives.

## Known limitations

- Mock data only. No live prices or live fee rules. Fees are modelled as one profile per platform and location, not as time-based surges or membership plans.
- No split-cart optimisation (buying different items on different apps).
- No authentication, so a cart is accessible to anyone who has its UUID.
- The Django admin requires `python manage.py createsuperuser`.
