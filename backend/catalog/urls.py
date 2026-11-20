from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryList.as_view()),
    path("locations/", views.LocationList.as_view()),
    path("platforms/", views.PlatformList.as_view()),
    path("products/", views.ProductList.as_view()),
    path("products/<int:pk>/compare/", views.ProductComparison.as_view()),
    path("carts/", views.CartCreate.as_view()),
    path("carts/<uuid:cart_id>/", views.CartDetail.as_view()),
    path("carts/<uuid:cart_id>/items/", views.CartItems.as_view()),
    path("carts/<uuid:cart_id>/items/<int:product_id>/", views.CartItemDetail.as_view()),
    path("carts/<uuid:cart_id>/compare/", views.CartComparison.as_view()),
]
