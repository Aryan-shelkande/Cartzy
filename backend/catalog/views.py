from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Category, Location, Platform, Product, ShoppingList, ShoppingListItem
from .serializers import (
    AddItemSerializer,
    CartComparisonSerializer,
    CategorySerializer,
    LocationSerializer,
    PlatformSerializer,
    ProductComparisonSerializer,
    ProductSerializer,
    ShoppingListSerializer,
    UpdateItemSerializer,
)

PRODUCT_ORDERING = {
    "name": [F("name").asc()],
    "price": [F("min_price").asc(nulls_last=True), "name"],
    "-price": [F("min_price").desc(nulls_last=True), "name"],
    "savings": [F("savings").desc(nulls_last=True), "name"],
    "popular": [F("popularity").desc(), "name"],
}


def get_location(request):
    slug = request.query_params.get("location")
    if not slug:
        raise ValidationError({"location": "This query parameter is required."})
    location = Location.objects.select_related("city").filter(slug=slug).first()
    if location is None:
        raise ValidationError({"location": f"Unknown location '{slug}'."})
    return location


def get_platforms(request):
    """Active platforms, optionally narrowed by ?platforms=slug1,slug2."""
    raw = request.query_params.get("platforms", "")
    slugs = [s.strip() for s in raw.split(",") if s.strip()]
    platforms = services.active_platforms(slugs)
    if slugs and len(platforms) != len(set(slugs)):
        unknown = set(slugs) - {p.slug for p in platforms}
        raise ValidationError({"platforms": f"Unknown platform(s): {', '.join(sorted(unknown))}."})
    return platforms


def parse_bool(request, name):
    value = request.query_params.get(name)
    if value is None or value == "":
        return None
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise ValidationError({name: "Use true or false."})


class ProductPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 60


class CategoryList(generics.ListAPIView):
    serializer_class = CategorySerializer
    pagination_class = None
    # Meta.ordering is ignored on aggregate queries, so order explicitly.
    queryset = Category.objects.annotate(product_count=Count("products")).order_by("sort_order", "name")


class LocationList(generics.ListAPIView):
    serializer_class = LocationSerializer
    pagination_class = None
    queryset = Location.objects.select_related("city")


class PlatformList(generics.ListAPIView):
    serializer_class = PlatformSerializer
    pagination_class = None
    queryset = Platform.objects.filter(is_active=True)


class ProductList(generics.ListAPIView):
    """Products with a price summary for the chosen location.

    Query params: location (required), search, category, platforms,
    available (true/false), featured (true/false), ordering, page, page_size.
    """

    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        params = self.request.query_params
        location = get_location(self.request)
        platforms = get_platforms(self.request)

        products = Product.objects.select_related("category")
        if search := params.get("search", "").strip():
            products = products.filter(
                Q(name__icontains=search) | Q(brand__icontains=search) | Q(generic_name__icontains=search)
                | Q(category__name__icontains=search) | Q(sku__iexact=search)
            )
        if category := params.get("category"):
            products = products.filter(category__slug=category)
        if parse_bool(self.request, "featured"):
            products = products.filter(is_featured=True)

        products = services.annotate_price_summary(products, location, platforms)
        products = services.annotate_alternatives_count(products)
        available = parse_bool(self.request, "available")
        if available is not None:
            products = products.filter(available_count__gt=0) if available else products.filter(available_count=0)

        ordering = params.get("ordering", "name")
        if ordering not in PRODUCT_ORDERING:
            raise ValidationError({"ordering": f"Choose one of: {', '.join(PRODUCT_ORDERING)}."})
        return products.order_by(*PRODUCT_ORDERING[ordering])


class ProductComparison(APIView):
    def get(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
        result = services.compare_product(product, get_location(request), get_platforms(request))
        return Response(ProductComparisonSerializer(result).data)


def _cart_response(shopping_list, status_code=status.HTTP_200_OK):
    shopping_list = ShoppingList.objects.prefetch_related("items__product__category").get(pk=shopping_list.pk)
    brand_groups = services.brand_alternatives([item.product for item in shopping_list.items.all()])
    data = ShoppingListSerializer(shopping_list, context={"brand_groups": brand_groups}).data
    return Response(data, status=status_code)


class CartCreate(APIView):
    def post(self, request):
        return _cart_response(ShoppingList.objects.create(), status.HTTP_201_CREATED)


class CartDetail(APIView):
    def get(self, request, cart_id):
        return _cart_response(get_object_or_404(ShoppingList, pk=cart_id))


class CartItems(APIView):
    def post(self, request, cart_id):
        """Add a product, or increase its quantity if already in the list."""
        cart = get_object_or_404(ShoppingList, pk=cart_id)
        data = AddItemSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        item, created = ShoppingListItem.objects.get_or_create(
            shopping_list=cart,
            product=data.validated_data["product"],
            defaults={"quantity": data.validated_data["quantity"]},
        )
        if not created:
            item.quantity = min(item.quantity + data.validated_data["quantity"], 99)
            item.save(update_fields=["quantity"])
        cart.save(update_fields=["updated_at"])
        return _cart_response(cart)

    def delete(self, request, cart_id):
        cart = get_object_or_404(ShoppingList, pk=cart_id)
        cart.items.all().delete()
        return _cart_response(cart)


class CartItemDetail(APIView):
    def patch(self, request, cart_id, product_id):
        """Change quantity, accept_alternatives, or switch to another brand (product_id)."""
        item = get_object_or_404(
            ShoppingListItem.objects.select_related("product"), shopping_list_id=cart_id, product_id=product_id
        )
        data = UpdateItemSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        changes = data.validated_data
        for field in ("quantity", "accept_alternatives"):
            if field in changes:
                setattr(item, field, changes[field])

        new_product = changes.get("product")
        if new_product and new_product.id != item.product_id:
            if not item.product.match_key or new_product.match_key != item.product.match_key:
                raise ValidationError({"product_id": "Choose another brand of the same item and size."})
            existing = item.shopping_list.items.filter(product=new_product).first()
            if existing:  # brand already in the list: merge into that line
                existing.quantity = min(existing.quantity + item.quantity, 99)
                existing.accept_alternatives = existing.accept_alternatives or item.accept_alternatives
                existing.save(update_fields=["quantity", "accept_alternatives"])
                item.delete()
                return _cart_response(item.shopping_list)
            item.product = new_product
        item.save()
        return _cart_response(item.shopping_list)

    def delete(self, request, cart_id, product_id):
        item = get_object_or_404(ShoppingListItem, shopping_list_id=cart_id, product_id=product_id)
        item.delete()
        return _cart_response(item.shopping_list)


class CartComparison(APIView):
    def get(self, request, cart_id):
        cart = get_object_or_404(ShoppingList, pk=cart_id)
        items = cart.items.select_related("product")
        result = services.compare_cart(items, get_location(request), get_platforms(request))
        return Response(CartComparisonSerializer(result).data)
