"""Deterministic mock price and fee generator for demonstration only.

This is the single place that invents prices and charges. A real integration
(official API, affiliate feed, licensed provider) would replace this module with
one that writes ProductPrice and PlatformCharges rows with its own `source`
value; the comparison service is unaffected.
"""

import hashlib
import random
from decimal import ROUND_HALF_UP, Decimal

from catalog.models import PlatformCharges, ProductPrice

# Typical discount off MRP and catalogue coverage per platform.
PLATFORM_PROFILE = {
    "zepto": (0.08, 0.90),
    "blinkit": (0.07, 0.92),
    "instamart": (0.06, 0.88),
    "amazon": (0.10, 0.80),
    "flipkart-minutes": (0.09, 0.72),
    "bigbasket": (0.11, 0.90),
    "jiomart": (0.12, 0.78),
}
DEFAULT_PROFILE = (0.07, 0.80)

# Price nudge and coverage multiplier per location.
LOCATION_PROFILE = {
    "viman-nagar": (0.02, 1.00),
    "hadapsar": (-0.01, 0.92),
    "kothrud": (0.01, 0.98),
    "shivajinagar": (0.00, 1.00),
    "central-pune": (-0.02, 0.95),
}
DEFAULT_LOCATION = (0.00, 0.90)

# Demo order charges per platform (rupees):
# delivery fee, free delivery above, handling fee, platform fee,
# small-cart fee, small-cart below, discount %, discount cap, discount min order.
CHARGES_PROFILE = {
    "zepto": (30, 199, 9, 4, 35, 99, 0, None, 0),
    "blinkit": (30, 199, 11, 2, 20, 99, 0, None, 0),
    "instamart": (35, 199, 12, 5, 25, 149, 5, 50, 499),
    "amazon": (49, 299, 0, 0, 0, 0, 10, 75, 699),
    "flipkart-minutes": (25, 149, 9, 3, 30, 99, 8, 60, 399),
    "bigbasket": (40, 249, 0, 5, 0, 0, 5, 40, 300),
    "jiomart": (29, 199, 0, 0, 25, 99, 3, 30, 249),
}
DEFAULT_CHARGES = (30, 199, 5, 0, 20, 99, 0, None, 0)


def _rng(*parts):
    """Stable RNG per listing so re-seeding gives the same demo data."""
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def mock_price(product, platform, location):
    discount, coverage = PLATFORM_PROFILE.get(platform.slug, DEFAULT_PROFILE)
    nudge, location_coverage = LOCATION_PROFILE.get(location.slug, DEFAULT_LOCATION)
    rng = _rng(product.sku, platform.slug, location.slug)

    factor = 1 - discount + rng.uniform(-0.06, 0.06) + nudge
    factor = min(factor, 1.0)  # never above MRP
    price = (Decimal(product.mrp) * Decimal(str(factor))).quantize(Decimal("1"), ROUND_HALF_UP)
    is_available = rng.random() < coverage * location_coverage
    return ProductPrice(
        product=product,
        platform=platform,
        location=location,
        price=max(price, Decimal("1")),
        is_available=is_available,
        source=ProductPrice.SOURCE_MOCK,
    )


def generate_mock_prices(products, platforms, locations):
    return [mock_price(prod, plat, loc) for prod in products for plat in platforms for loc in locations]


def mock_charges(platform, location):
    """Platform fees for one location: the platform profile nudged per location."""
    (delivery, free_above, handling, platform_fee, small_fee, small_below,
     pct, cap, min_order) = CHARGES_PROFILE.get(platform.slug, DEFAULT_CHARGES)
    rng = _rng("charges", platform.slug, location.slug)
    delivery = max(0, delivery + rng.choice([-10, -5, 0, 0, 5, 10]))
    handling = max(0, handling + rng.choice([-2, 0, 0, 2])) if handling else 0
    return PlatformCharges(
        platform=platform,
        location=location,
        delivery_fee=Decimal(delivery),
        free_delivery_above=Decimal(free_above) if free_above is not None else None,
        handling_fee=Decimal(handling),
        platform_fee=Decimal(platform_fee),
        small_cart_fee=Decimal(small_fee),
        small_cart_below=Decimal(small_below),
        discount_percent=Decimal(pct),
        discount_max=Decimal(cap) if cap is not None else None,
        discount_min_order=Decimal(min_order),
        source=ProductPrice.SOURCE_MOCK,
    )


def generate_mock_charges(platforms, locations):
    return [mock_charges(plat, loc) for plat in platforms for loc in locations]
