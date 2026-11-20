"""Browser smoke test for the Cartzy UI.

Needs both dev servers running (backend :8000 with seed data, frontend :5173) and
Python Playwright:  pip install playwright && playwright install chromium

    python e2e/ui_smoke.py
"""

import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

APP = os.environ.get("CARTZY_URL", "http://localhost:5173/")
API = os.environ.get("CARTZY_API", "http://localhost:8000/api")


def api_get(path):
    with urllib.request.urlopen(API + path) as res:
        return json.load(res)


def server_cart(page):
    cart_id = page.evaluate("localStorage.getItem('cartzy.cartId')")
    return {i["product"]["id"]: i["quantity"] for i in api_get(f"/carts/{cart_id}/")["items"]}


def fresh_page(browser, **kwargs):
    page = browser.new_page(**kwargs)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and page.errors.append(m.text))
    page.goto(APP)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_selector("#browse .product-card:not(.skeleton)")
    return page


def test_dashboard(browser):
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    headings = page.locator(".section-head h2").all_inner_texts()
    assert any("Best deals" in h for h in headings), headings
    assert any("Featured" in h for h in headings), headings
    categories = page.locator(".category span:last-child").all_inner_texts()
    assert categories[:3] == ["All", "Groceries", "Dairy"], categories
    assert page.locator(".demo-banner").is_visible()
    assert not page.errors, page.errors


def test_add_and_rapid_quantity_clicks(browser):
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    page.locator("#browse .btn-add").first.click()
    page.wait_for_selector("#browse .stepper")
    assert "Added" in page.locator(".toast").last.inner_text()

    plus = page.locator("#browse .stepper button[aria-label='Increase quantity']").first
    for _ in range(5):
        plus.click()  # no waiting between clicks
    page.wait_for_function("document.querySelector('.cart-badge')?.textContent === '6'")
    page.wait_for_timeout(1500)  # let queued requests finish
    assert page.locator(".cart-badge").inner_text() == "6"
    assert list(server_cart(page).values()) == [6], server_cart(page)


def test_product_comparison_drawer(browser):
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    page.locator("#browse .product-card-body").first.click()
    page.wait_for_selector(".offer")
    assert page.locator(".offer").count() == len(api_get("/platforms/"))
    assert page.locator(".offer-best").count() >= 1
    page.keyboard.press("Escape")
    assert page.locator(".drawer").count() == 0


def test_search_filters_and_empty_state(browser):
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    page.fill(".search input", "amul")
    page.wait_for_function("document.querySelector('#browse h2').textContent.includes('amul')")
    # Wait until the previous results are replaced, then check every card.
    page.wait_for_function("""(() => { const b = [...document.querySelectorAll('#browse .product-brand')];
        return b.length > 0 && !document.querySelector('#browse .skeleton')
            && b.every((el) => el.textContent.toLowerCase().includes('amul')) })()""")
    page.fill(".search input", "zzzz-nothing")
    page.wait_for_selector(".empty")
    page.click(".empty .btn")
    page.click(".category[data-category='dairy']")
    page.wait_for_function("document.querySelector('#browse h2').textContent === 'Dairy'")


def test_cart_comparison_and_location(browser):
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    for _ in range(4):
        page.locator("#browse .btn-add").first.click()
        page.wait_for_timeout(300)
    page.click(".cart-button")
    page.wait_for_selector(".pcard")
    assert page.locator(".pcard").count() == len(api_get("/platforms/"))
    assert page.locator(".pcard-best").count() <= 1
    assert page.locator(".pcard-best.pcard-incomplete").count() == 0  # a partial cart never wins
    for card in page.locator(".pcard").all():
        for label in ("Item subtotal", "Delivery fee", "Handling fee", "Platform fee", "Discount", "Final payable"):
            assert label in card.locator(".charges").inner_text(), label
    before = page.locator(".platform-grid").inner_text()
    page.select_option(".location-select-wrap select", "hadapsar")
    page.wait_for_function(f"document.querySelector('.platform-grid')?.innerText !== {json.dumps(before)}")
    page.locator(".cart-item .btn-link").first.click()
    page.wait_for_function("document.querySelectorAll('.cart-item').length === 3")


def test_brand_choice_and_alternatives(browser):
    """Search a generic item, change its brand, accept alternatives: the server cart follows each step."""
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    page.click(".quick-add:text('Salt')")
    page.wait_for_function("document.querySelector('#browse h2').textContent.includes('Salt')")
    page.locator("#browse .product-card", has_text="Tata Salt").locator(".btn-add").click()
    page.wait_for_selector(".cart-summary-active")
    page.click(".btn-compare")
    page.wait_for_selector(".pcard")

    salt = page.locator(".cart-item").first
    brands = salt.locator(".brand-select option").all_inner_texts()
    assert len(brands) >= 2 and "Tata" in brands, brands
    other = next(b for b in brands if b != "Tata")
    salt.locator(".brand-select select").select_option(label=other)
    page.wait_for_function(f"document.querySelector('.cart-item strong')?.textContent.includes({json.dumps(other)})")
    page.wait_for_timeout(800)
    (product_id,) = server_cart(page)
    assert api_get(f"/products/{product_id}/compare/?location=viman-nagar")["product"]["brand"] == other

    page.locator(".alt-toggle input").first.check()
    page.wait_for_timeout(1200)
    cart_id = page.evaluate("localStorage.getItem('cartzy.cartId')")
    assert api_get(f"/carts/{cart_id}/")["items"][0]["accept_alternatives"] is True
    page.locator(".pcard .btn-secondary").first.click()
    page.wait_for_selector(".pcard-lines .status-chip")
    assert not page.errors, page.errors


def test_confetti_on_milestone_only(browser):
    page = fresh_page(browser, viewport={"width": 1366, "height": 900})
    # The canvas only lives for the burst, so count insertions rather than polling for it.
    count_bursts = """window.__bursts = 0; new MutationObserver((records) => records.forEach((r) =>
        r.addedNodes.forEach((n) => { if (n.classList?.contains('confetti-canvas')) window.__bursts++ })
    )).observe(document.body, { childList: true })"""
    page.evaluate(count_bursts)
    page.locator(".rail .btn-add").first.click()  # top "best deal" product
    plus = page.locator(".rail .stepper button[aria-label='Increase quantity']").first
    for _ in range(4):
        page.wait_for_timeout(900)
        if page.evaluate("window.__bursts"):
            break
        plus.click()
    assert page.evaluate("window.__bursts") == 1, "confetti did not fire exactly once"

    page.reload()  # saved cart loads with savings above the milestone
    page.evaluate(count_bursts)
    page.wait_for_selector(".cart-summary-active .summary-total")
    page.wait_for_timeout(800)
    assert page.evaluate("window.__bursts") == 0, "confetti fired on page load"


def test_mobile_layout(browser):
    page = fresh_page(browser, viewport={"width": 390, "height": 844}, is_mobile=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#browse .btn-add").first.click()
    page.wait_for_selector(".cart-summary-active .btn")
    toast = page.locator(".toast").first.bounding_box()
    assert toast["y"] < 300, f"toast should sit near the top on mobile, got y={toast['y']}"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_")]
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, fn in tests:
            try:
                fn(browser)
                print(f"PASS {name}")
            except Exception as exc:  # report every test, not just the first failure
                failures += 1
                print(f"FAIL {name}: {exc}")
        browser.close()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
