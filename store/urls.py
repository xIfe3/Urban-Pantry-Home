from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<slug:slug>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/<slug:slug>/', views.toggle_wishlist, name='toggle_wishlist'),
]
