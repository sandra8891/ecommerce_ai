# urls.py
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('login', views.loginuser, name='loginuser'),
    path('adminindex', views.adminindex, name='adminindex'),
    path('users/', views.admin_users, name='admin_users'),
    path('usersignup', views.usersignup, name='usersignup'),
    path('forgotpassword', views.getusername, name='forgotpassword'),
    path('verifyotp', views.verifyotp, name='verifyotp'),
    path('gallery', views.gallery, name='gallery'),
    path('passwordreset', views.passwordreset, name='passwordreset'),
    path('logout', views.logoutuser, name="logoutuser"),
    path('', views.firstpage, name="firstpage"),
    path('products/<int:id>', views.products, name='products'),
    path('add_to_cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('dele/<int:id>/', views.delete_cart, name='dele'),
    path('about_us/', views.about_us, name='about_us'),
    path('home', views.home, name='home'),
    path('adminlogout', views.logoutadmin, name="adminlogout"),
    path('deletion/<int:id>/', views.delete_g, name='deletion'),
    path('edit/<int:pk>/', views.edit_g, name='edit_g'),
    path('cart ⟴/increment/<int:id>/', views.increment_cart, name='increment_cart'),
    path('cart/decrement/<int:id>/', views.decrement_cart, name='decrement_cart'),
    path('remove-from-wishlist/<int:id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('add-to-wishlist/<int:id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('search/', views.search_results, name='search_results'),
    path('myprofile/', views.myprofile, name='myprofile'),
    path('new-arrivals/', views.new_arrivals_page, name='new_arrivals_page'),
    path('category/<str:category>/', views.category_products, name='category_products'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('orders/', views.admin_orders, name='admin_orders'),
    path('checkout/', views.checkout, name='checkout'),
    path('razorpay_callback/', views.razorpay_callback, name='razorpay_callback'),
    # path('admin/orders/', views.admin_orders, name='admin_orders'),
    

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)