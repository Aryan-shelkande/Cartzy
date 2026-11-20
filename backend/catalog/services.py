"""Price comparison logic shared by the API views.

Everything here reads `ProductPrice` and `PlatformCharges` rows only, so swapping
the mock seed for a licensed feed (which would write the same rows) needs no
changes in this module.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, F, Max, Min, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from .models import Platform, PlatformCharges, Product, ProductPrice

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

# Line statuses in a cart comparison.
EXACT = "exact"  # the requested brand and size
ALTERNATIVE = "alternative"  # another brand the user accepted; counted in the total
ALTERNATIVE_AVAILABLE = "alternative_available"  # another brand exists but is not accepted; not counted
UNAVAILABLE = "unavailable"  # neither the product nor an alternative is in stock


def active_platforms(slugs=None):
    platforms = Platform.objects.filter(is_active=True)
    if slugs:
        platforms = platforms.filter(slug__in=slugs)
    return list(platforms)


def annotate_price_summary(queryset, location, platforms):
    """Add min_price, max_price, savings and available_count for one location."""
    available = Q(
        prices__location=location,
        prices__is_available=True,
        prices__platform__in=platforms,
    )
    return queryset.annotate(
        min_price=Min("prices__price", filter=available),
        max_price=Max("prices__price", filter=available),
        available_count=Count("prices", filter=available),
    ).annotate(savings=F("max_price") - F("min_price"))


def annotate_alternatives_count(queryset):
    """Add alternatives_count: how many other brands share the product's match_key."""
    siblings = (
        Product.objects.filter(match_key=OuterRef("match_key"))
        .exclude(match_key="")
        .exclude(pk=OuterRef("pk"))
        .order_by()
        .values("match_key")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return queryset.annotate(alternatives_count=Coalesce(Subquery(siblings), 0))


def brand_alternatives(products):
    """{match_key: [products]} for the given products' match keys, ordered by brand."""
    keys = {p.match_key for p in products if p.match_key}
    groups = defaultdict(list)
    for product in Product.objects.filter(match_key__in=keys).select_related("category").order_by("brand", "id"):
        groups[product.match_key].append(product)
    return groups


def _price_map(product_ids, location, platforms):
    rows = ProductPrice.objects.filter(
        product_id__in=product_ids, location=location, platform__in=platforms
    )
    return {(row.product_id, row.platform_id): row for row in rows}


def _offer(platform, row):
    return {
        "platform": platform,
        "price": row.price if row else None,
        "is_available": bool(row and row.is_available),
        "updated_at": row.updated_at if row else None,
        "source": row.source if row else None,
    }


def compare_product(product, location, platforms):
    """Offers for one product on every given platform, cheapest first.

    Platforms with no listing are returned as unavailable rather than dropped.
    Other brands of the same item and size are listed separately, never mixed
    into the offers.
    """
    prices = _price_map([product.id], location, platforms)
    offers = [_offer(p, prices.get((product.id, p.id))) for p in platforms]

    available_prices = [o["price"] for o in offers if o["is_available"]]
    cheapest = min(available_prices, default=None)
    highest = max(available_prices, default=None)
    for offer in offers:
        offer["is_cheapest"] = offer["is_available"] and offer["price"] == cheapest

    offers.sort(key=lambda o: (not o["is_available"], o["price"] or 0))
    alternatives = []
    if product.match_key:
        alternatives = list(
            annotate_price_summary(
                Product.objects.filter(match_key=product.match_key).exclude(pk=product.pk).select_related("category"),
                location,
                platforms,
            ).order_by(F("min_price").asc(nulls_last=True), "brand")
        )
    return {
        "product": product,
        "alternatives": alternatives,
        "location": location,
        "offers": offers,
        "cheapest_price": cheapest,
        "highest_price": highest,
        "savings": (highest - cheapest) if cheapest is not None else None,
        "available_count": len(available_prices),
        "is_demo_data": any(o["source"] == ProductPrice.SOURCE_MOCK for o in offers),
    }


def calculate_charges(subtotal, charges):
    """Fees, discount and final payable amount for one order on one platform.

    `charges` is a PlatformCharges row, or None when the platform has no fees
    configured for the location. An empty order costs nothing.

        total = subtotal + delivery + handling + platform fee + other charges - discount
    """
    subtotal = Decimal(subtotal).quantize(CENT)
    delivery = handling = platform_fee = other = discount = ZERO
    free_above = None
    if charges is not None and subtotal > 0:
        free_above = charges.free_delivery_above
        delivery = ZERO if free_above is not None and subtotal >= free_above else charges.delivery_fee
        handling = charges.handling_fee
        platform_fee = charges.platform_fee
        if subtotal < charges.small_cart_below:
            other = charges.small_cart_fee
        if charges.discount_percent and subtotal >= charges.discount_min_order:
            # Whole rupees, as the apps show them.
            discount = (subtotal * charges.discount_percent / 100).quantize(Decimal("1"), ROUND_HALF_UP)
            if charges.discount_max is not None:
                discount = min(discount, charges.discount_max)
            discount = min(discount, subtotal)

    fees = delivery + handling + platform_fee + other
    return {
        "subtotal": subtotal,
        "delivery_fee": delivery,
        "handling_fee": handling,
        "platform_fee": platform_fee,
        "other_charges": other,
        "discount": discount,
        "fees_total": fees,
        "total": subtotal + fees - discount,
        "free_delivery_above": free_above,
    }


def _match_line(item, platform, prices, alternatives):
    """What the platform can supply for one list item: (status, product, unit price).

    The requested product wins whenever it is in stock. Otherwise the cheapest
    in-stock brand with the same match_key is offered, and it only counts
    towards the total if the user accepted alternatives for this item.
    """
    row = prices.get((item.product_id, platform.id))
    if row and row.is_available:
        return EXACT, item.product, row.price

    options = []
    for alt in alternatives.get(item.product.match_key, []):
        alt_row = prices.get((alt.id, platform.id))
        if alt.id != item.product_id and alt_row and alt_row.is_available:
            options.append((alt_row.price, alt.id, alt))
    if not options:
        return UNAVAILABLE, None, None
    price, _, alt = min(options, key=lambda o: (o[0], o[1]))
    return (ALTERNATIVE if item.accept_alternatives else ALTERNATIVE_AVAILABLE), alt, price


def compare_cart(items, location, platforms):
    """Final payable amount of the whole list on each platform.

    `items` is an iterable of objects with `.product`, `.quantity` and
    `.accept_alternatives`. A platform is complete only when every item is the
    exact product or an accepted alternative brand. Incomplete carts are
    reported with what is missing and are never ranked against complete ones,
    so a partial total can't pass as the cheapest option.
    """
    items = list(items)
    alternatives = brand_alternatives([i.product for i in items])
    product_ids = {i.product_id for i in items} | {p.id for group in alternatives.values() for p in group}
    prices = _price_map(product_ids, location, platforms)
    charges_by_platform = {
        c.platform_id: c for c in PlatformCharges.objects.filter(location=location, platform__in=platforms)
    }

    carts = []
    for platform in platforms:
        subtotal = Decimal("0")
        lines = []
        counts = defaultdict(int)
        for item in items:
            status, matched, unit_price = _match_line(item, platform, prices, alternatives)
            counted = status in (EXACT, ALTERNATIVE)
            line_total = unit_price * item.quantity if counted else None
            if counted:
                subtotal += line_total
            counts[status] += 1
            lines.append(
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "status": status,
                    "matched_product": matched,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "is_available": counted,
                    "accept_alternatives": item.accept_alternatives,
                }
            )

        available = counts[EXACT] + counts[ALTERNATIVE]
        charges = calculate_charges(subtotal, charges_by_platform.get(platform.id))
        carts.append(
            {
                "platform": platform,
                "total": charges["total"],
                "subtotal": charges["subtotal"],
                "charges": charges,
                "is_complete": bool(items) and available == len(items),
                "is_exact_match": bool(items) and counts[EXACT] == len(items),
                # Every gap could be filled by accepting another brand.
                "would_complete_with_alternatives": available < len(items) and counts[UNAVAILABLE] == 0,
                "requested_items": len(items),
                "available_items": available,
                "exact_items": counts[EXACT],
                "alternative_items": counts[ALTERNATIVE],
                "alternative_available_items": counts[ALTERNATIVE_AVAILABLE],
                "unavailable_items": counts[UNAVAILABLE],
                "missing_products": [i.product for i, line in zip(items, lines) if not line["is_available"]],
                "lines": lines,
                "extra_vs_cheapest": None,
            }
        )

    carts.sort(
        key=lambda c: (
            not c["is_complete"],
            0 if c["is_complete"] else len(c["missing_products"]),
            c["total"],
            c["alternative_items"],  # equal totals: prefer more exact brands
        )
    )
    complete = [c for c in carts if c["is_complete"]]
    cheapest = complete[0] if complete else None
    highest = max(complete, key=lambda c: c["total"]) if complete else None
    if highest is not None and highest["total"] == cheapest["total"]:
        highest = None  # one complete cart, or all tied: nothing to contrast
    exact = [c for c in complete if c["is_exact_match"]]
    for cart in carts:
        cart["is_cheapest"] = cart is cheapest
        cart["is_highest"] = cart is highest
        if cart["is_complete"]:
            cart["extra_vs_cheapest"] = cart["total"] - cheapest["total"]

    return {
        "location": location,
        "item_count": len(items),
        "unit_count": sum(i.quantity for i in items),
        "platforms": carts,
        "complete_count": len(complete),
        "cheapest_platform": cheapest["platform"] if cheapest else None,
        "cheapest_total": cheapest["total"] if cheapest else None,
        "highest_platform": highest["platform"] if highest else None,
        "highest_total": highest["total"] if highest else None,
        "savings": (highest["total"] - cheapest["total"]) if highest else (ZERO if cheapest else None),
        "cheapest_exact_platform": exact[0]["platform"] if exact else None,
        "cheapest_exact_total": exact[0]["total"] if exact else None,
        "is_demo_data": any(r.source == ProductPrice.SOURCE_MOCK for r in prices.values())
        or any(c.source == ProductPrice.SOURCE_MOCK for c in charges_by_platform.values()),
    }
