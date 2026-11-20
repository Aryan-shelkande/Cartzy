from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from rest_framework.test import APIClient

from . import services
from .models import Category, City, Location, Platform, PlatformCharges, Product, ProductPrice


class ComparisonFixture(TestCase):
    """Two products, three platforms, one location, hand-picked prices."""

    @classmethod
    def setUpTestData(cls):
        city = City.objects.create(name="Pune")
        cls.loc = Location.objects.create(city=city, name="Kothrud", slug="kothrud")
        cat = Category.objects.create(name="Dairy", slug="dairy", icon="🥛")
        cls.zepto = Platform.objects.create(name="Zepto", slug="zepto", color="#000000", sort_order=0)
        cls.blinkit = Platform.objects.create(name="Blinkit", slug="blinkit", color="#000000", sort_order=1)
        cls.amazon = Platform.objects.create(name="Amazon", slug="amazon", color="#000000", sort_order=2)
        cls.milk = Product.objects.create(sku="M1", name="Milk", brand="Amul", category=cat, quantity="500 ml", mrp=30)
        cls.butter = Product.objects.create(sku="B1", name="Butter", brand="Amul", category=cat, quantity="100 g", mrp=60)

        def price(product, platform, amount, available=True):
            ProductPrice.objects.create(
                product=product, platform=platform, location=cls.loc,
                price=Decimal(amount), is_available=available,
            )

        price(cls.milk, cls.zepto, "27")
        price(cls.milk, cls.blinkit, "25")
        price(cls.milk, cls.amazon, "20", available=False)  # cheapest, but out of stock
        price(cls.butter, cls.zepto, "55")
        price(cls.butter, cls.blinkit, "58")
        # butter has no Amazon listing at all

    def setUp(self):
        self.client = APIClient()


class ProductComparisonTests(ComparisonFixture):
    def test_cheapest_ignores_unavailable_and_lists_all_platforms(self):
        res = self.client.get(f"/api/products/{self.milk.id}/compare/", {"location": "kothrud"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["cheapest_price"], "25.00")
        self.assertEqual(data["highest_price"], "27.00")
        self.assertEqual(data["savings"], "2.00")
        self.assertEqual(data["product"]["sku"], "M1")  # exact product, no substitute
        self.assertEqual([o["platform"]["slug"] for o in data["offers"]], ["blinkit", "zepto", "amazon"])
        self.assertTrue(data["offers"][0]["is_cheapest"])
        self.assertFalse(data["offers"][2]["is_available"])
        self.assertTrue(data["is_demo_data"])

    def test_missing_listing_is_reported_unavailable(self):
        data = self.client.get(f"/api/products/{self.butter.id}/compare/", {"location": "kothrud"}).json()
        amazon = next(o for o in data["offers"] if o["platform"]["slug"] == "amazon")
        self.assertFalse(amazon["is_available"])
        self.assertIsNone(amazon["price"])

    def test_platform_filter(self):
        data = self.client.get(
            f"/api/products/{self.milk.id}/compare/", {"location": "kothrud", "platforms": "zepto"}
        ).json()
        self.assertEqual(len(data["offers"]), 1)
        self.assertEqual(data["cheapest_price"], "27.00")

    def test_location_validation(self):
        res = self.client.get(f"/api/products/{self.milk.id}/compare/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("location", res.json()["error"]["details"])
        res = self.client.get(f"/api/products/{self.milk.id}/compare/", {"location": "nowhere"})
        self.assertEqual(res.status_code, 400)
        res = self.client.get("/api/products/999/compare/", {"location": "kothrud"})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["error"]["status"], 404)


class ProductListTests(ComparisonFixture):
    def test_summary_search_and_sorting(self):
        data = self.client.get("/api/products/", {"location": "kothrud", "ordering": "-price"}).json()
        self.assertEqual(data["count"], 2)
        self.assertEqual([p["sku"] for p in data["results"]], ["B1", "M1"])
        self.assertEqual(data["results"][1]["min_price"], "25.00")
        self.assertEqual(data["results"][1]["available_count"], 2)

        data = self.client.get("/api/products/", {"location": "kothrud", "search": "butt"}).json()
        self.assertEqual([p["sku"] for p in data["results"]], ["B1"])

    def test_availability_filter_respects_platforms(self):
        data = self.client.get(
            "/api/products/", {"location": "kothrud", "platforms": "amazon", "available": "false"}
        ).json()
        self.assertEqual(data["count"], 2)

    def test_invalid_params(self):
        for params in ({"location": "kothrud", "ordering": "bogus"},
                       {"location": "kothrud", "platforms": "nope"},
                       {"location": "kothrud", "available": "maybe"}):
            self.assertEqual(self.client.get("/api/products/", params).status_code, 400, params)


class CartTests(ComparisonFixture):
    def make_cart(self, *items):
        cart_id = self.client.post("/api/carts/").json()["id"]
        for product, qty in items:
            res = self.client.post(
                f"/api/carts/{cart_id}/items/", {"product_id": product.id, "quantity": qty}, format="json"
            )
            self.assertEqual(res.status_code, 200)
        return cart_id

    def test_item_management(self):
        cart_id = self.make_cart((self.milk, 1), (self.milk, 2))
        items = self.client.get(f"/api/carts/{cart_id}/").json()["items"]
        self.assertEqual(items[0]["quantity"], 3)

        res = self.client.patch(f"/api/carts/{cart_id}/items/{self.milk.id}/", {"quantity": 5}, format="json")
        self.assertEqual(res.json()["items"][0]["quantity"], 5)
        res = self.client.patch(f"/api/carts/{cart_id}/items/{self.milk.id}/", {"quantity": 0}, format="json")
        self.assertEqual(res.status_code, 400)

        res = self.client.delete(f"/api/carts/{cart_id}/items/{self.milk.id}/")
        self.assertEqual(res.json()["items"], [])

        res = self.client.post(f"/api/carts/{cart_id}/items/", {"product_id": 999}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cart_totals_and_incomplete_platforms(self):
        cart_id = self.make_cart((self.milk, 2), (self.butter, 1))
        data = self.client.get(f"/api/carts/{cart_id}/compare/", {"location": "kothrud"}).json()
        by_slug = {c["platform"]["slug"]: c for c in data["platforms"]}

        self.assertEqual(by_slug["zepto"]["total"], "109.00")    # 2*27 + 55
        self.assertEqual(by_slug["blinkit"]["total"], "108.00")  # 2*25 + 58
        self.assertTrue(by_slug["blinkit"]["is_cheapest"])
        self.assertEqual(data["cheapest_platform"]["slug"], "blinkit")
        self.assertEqual(data["savings"], "1.00")

        amazon = by_slug["amazon"]
        self.assertFalse(amazon["is_complete"])
        self.assertEqual(amazon["available_items"], 0)
        self.assertEqual({p["id"] for p in amazon["missing_products"]}, {self.milk.id, self.butter.id})
        self.assertEqual(data["platforms"][-1]["platform"]["slug"], "amazon")  # incomplete ranked last

    def test_empty_cart_has_no_winner(self):
        cart_id = self.make_cart()
        data = self.client.get(f"/api/carts/{cart_id}/compare/", {"location": "kothrud"}).json()
        self.assertIsNone(data["cheapest_platform"])
        self.assertFalse(any(c["is_complete"] for c in data["platforms"]))


class SeedTests(TestCase):
    def test_seed_is_complete_and_repeatable(self):
        call_command("seed_data", stdout=StringIO())
        first = list(ProductPrice.objects.order_by("id").values_list("price", "is_available"))
        self.assertEqual(Platform.objects.count(), 7)
        self.assertEqual(Location.objects.count(), 5)
        self.assertGreaterEqual(Product.objects.count(), 50)
        self.assertEqual(ProductPrice.objects.count(), 7 * 5 * Product.objects.count())
        self.assertTrue(ProductPrice.objects.filter(is_available=False).exists())
        for p in ProductPrice.objects.select_related("product")[:200]:
            self.assertLessEqual(p.price, p.product.mrp)
        self.assertEqual(PlatformCharges.objects.count(), 7 * 5)
        self.assertFalse(Product.objects.filter(match_key="").exists())
        self.assertTrue(Product.objects.values("match_key").annotate(n=Count("id")).filter(n__gt=1).exists())

        call_command("seed_data", stdout=StringIO())
        second = list(ProductPrice.objects.order_by("id").values_list("price", "is_available"))
        self.assertEqual(first, second)


class BrandMatchingFixture(TestCase):
    """The README scenario on three platforms: A has every exact brand, B has
    salt only in other brands, C has no salt at all."""

    @classmethod
    def setUpTestData(cls):
        city = City.objects.create(name="Pune")
        cls.loc = Location.objects.create(city=city, name="Hadapsar", slug="hadapsar")
        cat = Category.objects.create(name="Groceries", slug="groceries", icon="🌾")
        cls.a = Platform.objects.create(name="A", slug="a", color="#000000", sort_order=0)
        cls.b = Platform.objects.create(name="B", slug="b", color="#000000", sort_order=1)
        cls.c = Platform.objects.create(name="C", slug="c", color="#000000", sort_order=2)

        def product(sku, brand, key, mrp):
            return Product.objects.create(
                sku=sku, name=f"{brand} {key}", brand=brand, category=cat,
                quantity="1 kg", mrp=mrp, match_key=key,
            )

        cls.tata_salt = product("S1", "Tata", "salt-1-kg", 30)
        cls.alt_salt = product("S2", "Aashirvaad", "salt-1-kg", 30)
        cls.cheap_salt = product("S3", "Annapurna", "salt-1-kg", 30)
        cls.sugar = product("G1", "Madhur", "sugar-1-kg", 60)

        def price(prod, platform, amount, available=True):
            ProductPrice.objects.create(
                product=prod, platform=platform, location=cls.loc, price=Decimal(amount), is_available=available
            )

        price(cls.tata_salt, cls.a, "28")
        price(cls.sugar, cls.a, "55")
        price(cls.tata_salt, cls.b, "20", available=False)  # requested brand out of stock
        price(cls.alt_salt, cls.b, "24")
        price(cls.cheap_salt, cls.b, "22")  # the cheapest alternative is offered
        price(cls.sugar, cls.b, "52")
        price(cls.sugar, cls.c, "50")  # no salt of any brand on C

    def setUp(self):
        self.client = APIClient()
        self.cart_id = self.client.post("/api/carts/").json()["id"]
        for prod in (self.tata_salt, self.sugar):
            self.client.post(f"/api/carts/{self.cart_id}/items/", {"product_id": prod.id}, format="json")

    def compare(self):
        data = self.client.get(f"/api/carts/{self.cart_id}/compare/", {"location": "hadapsar"}).json()
        return data, {c["platform"]["slug"]: c for c in data["platforms"]}

    def accept_salt_alternatives(self, accept=True):
        return self.client.patch(
            f"/api/carts/{self.cart_id}/items/{self.tata_salt.id}/", {"accept_alternatives": accept}, format="json"
        )


class BrandMatchingTests(BrandMatchingFixture):
    def test_alternatives_are_offered_but_not_counted_until_accepted(self):
        data, carts = self.compare()
        a, b, c = carts["a"], carts["b"], carts["c"]

        self.assertTrue(a["is_complete"] and a["is_exact_match"])
        self.assertEqual((a["exact_items"], a["alternative_items"], a["unavailable_items"]), (2, 0, 0))

        salt_b = next(line for line in b["lines"] if line["product_id"] == self.tata_salt.id)
        self.assertEqual(salt_b["status"], "alternative_available")
        self.assertEqual(salt_b["matched_product"]["brand"], "Annapurna")
        self.assertEqual(salt_b["unit_price"], "22.00")
        self.assertIsNone(salt_b["line_total"])  # never silently substituted
        self.assertFalse(b["is_complete"])
        self.assertTrue(b["would_complete_with_alternatives"])
        self.assertEqual(b["subtotal"], "52.00")
        self.assertEqual(b["alternative_available_items"], 1)

        self.assertFalse(c["is_complete"])
        self.assertFalse(c["would_complete_with_alternatives"])
        self.assertEqual(c["unavailable_items"], 1)
        self.assertEqual([p["id"] for p in c["missing_products"]], [self.tata_salt.id])

        # The partial carts are cheaper than A's full cart (83) but must not win.
        self.assertEqual(data["cheapest_platform"]["slug"], "a")
        self.assertEqual(data["complete_count"], 1)
        self.assertIsNone(data["highest_platform"])
        self.assertEqual(data["savings"], "0.00")
        self.assertEqual([x["platform"]["slug"] for x in data["platforms"]], ["a", "c", "b"])

    def test_accepting_alternatives_recalculates_and_ranks(self):
        res = self.accept_salt_alternatives()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["items"][0]["accept_alternatives"])

        data, carts = self.compare()
        b = carts["b"]
        self.assertTrue(b["is_complete"])
        self.assertFalse(b["is_exact_match"])
        self.assertEqual((b["exact_items"], b["alternative_items"]), (1, 1))
        salt_b = next(line for line in b["lines"] if line["product_id"] == self.tata_salt.id)
        self.assertEqual((salt_b["status"], salt_b["line_total"]), ("alternative", "22.00"))
        self.assertEqual(b["total"], "74.00")  # 22 alternative salt + 52 sugar
        self.assertEqual(data["cheapest_platform"]["slug"], "b")
        self.assertEqual(data["highest_platform"]["slug"], "a")
        self.assertEqual(data["savings"], "9.00")
        self.assertEqual(carts["a"]["extra_vs_cheapest"], "9.00")
        self.assertEqual(data["cheapest_exact_platform"]["slug"], "a")
        self.assertFalse(carts["c"]["is_complete"])  # nothing to substitute on C

        self.accept_salt_alternatives(False)
        _, carts = self.compare()
        self.assertFalse(carts["b"]["is_complete"])

    def test_change_brand(self):
        url = f"/api/carts/{self.cart_id}/items/{self.tata_salt.id}/"
        res = self.client.patch(url, {"product_id": self.alt_salt.id}, format="json")
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        self.assertEqual(items[0]["product"]["id"], self.alt_salt.id)
        self.assertEqual({o["brand"] for o in items[0]["brand_options"]}, {"Tata", "Aashirvaad", "Annapurna"})

        # A different item is not a brand alternative.
        url = f"/api/carts/{self.cart_id}/items/{self.alt_salt.id}/"
        res = self.client.patch(url, {"product_id": self.sugar.id}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.client.patch(url, {}, format="json").status_code, 400)

    def test_change_brand_merges_with_existing_line(self):
        self.client.post(
            f"/api/carts/{self.cart_id}/items/", {"product_id": self.alt_salt.id, "quantity": 2}, format="json"
        )
        res = self.client.patch(
            f"/api/carts/{self.cart_id}/items/{self.tata_salt.id}/", {"product_id": self.alt_salt.id}, format="json"
        )
        quantities = {i["product"]["id"]: i["quantity"] for i in res.json()["items"]}
        self.assertEqual(quantities, {self.alt_salt.id: 3, self.sugar.id: 1})

    def test_product_comparison_lists_other_brands(self):
        data = self.client.get(f"/api/products/{self.tata_salt.id}/compare/", {"location": "hadapsar"}).json()
        self.assertEqual([p["brand"] for p in data["alternatives"]], ["Annapurna", "Aashirvaad"])
        self.assertEqual(data["alternatives"][0]["min_price"], "22.00")
        listed = self.client.get("/api/products/", {"location": "hadapsar", "search": "tata"}).json()
        self.assertEqual(listed["results"][0]["alternatives_count"], 2)


class ChargesTests(BrandMatchingFixture):
    def test_calculate_charges_formula(self):
        rules = PlatformCharges(
            delivery_fee=Decimal("30"), free_delivery_above=Decimal("199"), handling_fee=Decimal("9"),
            platform_fee=Decimal("4"), small_cart_fee=Decimal("25"), small_cart_below=Decimal("99"),
            discount_percent=Decimal("10"), discount_max=Decimal("40"), discount_min_order=Decimal("150"),
        )
        small = services.calculate_charges(Decimal("80"), rules)
        self.assertEqual(
            (small["delivery_fee"], small["other_charges"], small["discount"], small["total"]),
            (Decimal("30"), Decimal("25"), Decimal("0"), Decimal("148")),  # 80 + 30 + 9 + 4 + 25
        )
        mid = services.calculate_charges(Decimal("160"), rules)
        self.assertEqual(mid["discount"], Decimal("16"))
        self.assertEqual(mid["total"], Decimal("187"))  # 160 + 30 + 9 + 4 - 16
        big = services.calculate_charges(Decimal("500"), rules)
        self.assertEqual((big["delivery_fee"], big["discount"]), (Decimal("0"), Decimal("40")))  # free, capped
        self.assertEqual(big["total"], Decimal("473"))  # 500 + 9 + 4 - 40

        self.assertEqual(services.calculate_charges(Decimal("0"), rules)["total"], Decimal("0"))
        self.assertEqual(services.calculate_charges(Decimal("50"), None)["total"], Decimal("50"))

    def test_fees_decide_the_cheapest_cart(self):
        self.accept_salt_alternatives()
        # B's items are cheaper (74 vs 83), but its fees make it the dearer cart.
        PlatformCharges.objects.create(platform=self.a, location=self.loc, delivery_fee=Decimal("10"))
        PlatformCharges.objects.create(
            platform=self.b, location=self.loc, delivery_fee=Decimal("25"), handling_fee=Decimal("5")
        )
        data, carts = self.compare()
        self.assertEqual(carts["a"]["total"], "93.00")
        self.assertEqual(carts["b"]["subtotal"], "74.00")
        self.assertEqual(carts["b"]["charges"]["fees_total"], "30.00")
        self.assertEqual(carts["b"]["total"], "104.00")
        self.assertEqual(data["cheapest_platform"]["slug"], "a")
        self.assertEqual(data["savings"], "11.00")
        self.assertTrue(carts["b"]["is_highest"])
