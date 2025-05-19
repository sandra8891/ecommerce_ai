class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Gallery, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)






from django.shortcuts import render, redirect
from .models import Cart, Gallery
from django.contrib import messages

# Add item to the cart
def add_to_cart(request, id):
    gallery_item = Gallery.objects.get(pk=id)
    
    if request.user.is_authenticated:
        cart_item, created = Cart.objects.get_or_create(user=request.user, item=gallery_item)
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        messages.success(request, f"{gallery_item.name} added to cart!")
        return redirect('firstpage')
    else:
        messages.error(request, "You need to be logged in to add items to the cart.")
        return redirect('loginuser')

# Update cart item quantity (increment or decrement)
def update_cart(request, id, action):
    try:
        cart_item = Cart.objects.get(user=request.user, item__id=id)
        if action == 'increment':
            cart_item.quantity += 1
        elif action == 'decrement' and cart_item.quantity > 1:
            cart_item.quantity -= 1
        cart_item.save()
    except Cart.DoesNotExist:
        messages.error(request, "Cart item not found.")
    return redirect('cart_view')

# Remove item from cart
def remove_from_cart(request, id):
    try:
        cart_item = Cart.objects.get(user=request.user, item__id=id)
        cart_item.delete()
        messages.success(request, "Item removed from cart.")
    except Cart.DoesNotExist:
        messages.error(request, "Cart item not found.")
    return redirect('cart_view')

# View the cart page
def cart_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "You need to be logged in to view the cart.")
        return redirect('loginuser')
    
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.total_price() for item in cart_items)
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})







urlpatterns = [
    # Other paths...
    path('addtocart/<int:id>/', views.add_to_cart, name='addtocart'),
    path('updatecart/<int:id>/<str:action>/', views.update_cart, name='updatecart'),
    path('removefromcart/<int:id>/', views.remove_from_cart, name='removefromcart'),
    path('cart/', views.cart_view, name='cart_view'),
    # Other paths...
]



userindex.html


<!-- Cart icon with item count -->
<div class="cart-icon">
    <i class="bi bi-cart-fill"></i>
    <span>{{ cart_item_count }}</span> <!-- Display the cart item count -->
</div>

<!-- Add to cart buttons for each product -->
<div class="gallery-grid">
    {% for i in gallery_images %}
    <div>
        <a href="{% url 'products' i.id %}">
            <img src="{{ i.feedimage.url }}" alt="Gallery Image" width="300"><br>
            <span>{{ i.name }}</span><br>
            <span>{{ i.model }}</span><br>
            <span>{{ i.price}}</span>
        </a>
        <a href="{% url 'addtocart' i.id %}">
            <button class="add-to-cart">Add to Cart</button>
        </a>
    </div>
    {% endfor %}
</div>


cart.html

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cart</title>
    <link rel="stylesheet" href="{% static 'css/cart.css' %}">
</head>
<body>

    <div class="cart-container">
        <h1>Your Cart</h1>
        {% if cart_items %}
        <div class="cart-items">
            {% for item in cart_items %}
            <div class="cart-item">
                <img src="{{ item.item.feedimage.url }}" alt="{{ item.item.name }}" width="100">
                <div class="item-details">
                    <p>{{ item.item.name }}</p>
                    <p>{{ item.item.model }}</p>
                    <p>{{ item.item.price }} $</p>

                    <div class="quantity">
                        <a href="{% url 'updatecart' item.item.id 'increment' %}">+</a>
                        <span>{{ item.quantity }}</span>
                        <a href="{% url 'updatecart' item.item.id 'decrement' %}">-</a>
                    </div>
                </div>
                <a href="{% url 'removefromcart' item.item.id %}">
                    <button>Remove</button>
                </a>
            </div>
            {% endfor %}
        </div>

        <div class="total-price">
            <h3>Total: ${{ total_price }}</h3>
        </div>
        
        <a href="{% url 'checkout' %}">
            <button class="buy-button">Proceed to Checkout</button>
        </a>
        {% else %}
        <p>Your cart is empty.</p>
        {% endif %}
    </div>

</body>
</html>

Step 6: Cart Icon Count

def get_cart_item_count(request):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
    else:
        cart_count = 0
    return cart_count

Then, pass cart_item_count to your templates in the context of your views

def firstpage(request): 
    gallery_images = Gallery.objects.all()
    cart_item_count = get_cart_item_count(request)
    return render(request, "userindex.html", {"gallery_images": gallery_images, "cart_item_count": cart_item_count})

1. Create a Search Form

from django import forms

class SearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=False, label="Search")


from .forms import SearchForm
from .models import Gallery

def firstpage(request): 
    gallery_images = Gallery.objects.all()

    # Handling the search query
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        query = search_form.cleaned_data['query']
        if query:
            gallery_images = gallery_images.filter(name__icontains=query)  # Search by name
            # You can also add other filters like:
            # .filter(model__icontains=query) if you want to search by model as well

    return render(request, "userindex.html", {"gallery_images": gallery_images, "search_form": search_form})


userindex.html

<form method="get" action="{% url 'firstpage' %}">
    {% csrf_token %}
    <input type="text" name="query" placeholder="Search products..." value="{{ request.GET.query }}">
    <button type="submit">Search</button>
</form>


userindex.html

<div class="gallery-grid">
    {% for i in gallery_images %}
    <div>
        <a href="{% url 'products' i.id %}">
            <img src="{{ i.feedimage.url }}" alt="Gallery Image" width="300"><br>
            <span>{{ i.name }}</span><br>
            <span>{{ i.model }}</span><br>
            <span>{{ i.price }}</span>
        </a>
        <a href="{% url 'addtocart' i.id %}">
            <button class="add-to-cart">Add to Cart</button>
        </a>
    </div>
    {% endfor %}
</div>


{% if gallery_images %}
    <div>
        <h1>Search Results</h1>
        <div class="gallery-grid">
            {% for i in gallery_images %}
            <div>
                <a href="{% url 'products' i.id %}">
                    <img src="{{ i.feedimage.url }}" alt="Gallery Image" width="300"><br>
                    <span>{{ i.name }}</span><br>
                    <span>{{ i.model }}</span><br>
                    <span>{{ i.price }}</span>
                </a>
                <a href="{% url 'addtocart' i.id %}">
                    <button class="add-to-cart">Add to Cart</button>
                </a>
            </div>
            {% endfor %}
        </div>
    </div>
{% else %}
    <p>No products found.</p>
{% endif %}



__________________________________________________________________________________________________________________________________


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, CartItem

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size')  # Get the selected size from the form
    if size:
        # Check if the product with the selected size already exists in the cart
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            size=size,
            defaults={'quantity': 1}
        )
        if not created:
            # If the item already exists in the cart, increment the quantity
            cart_item.quantity += 1
            cart_item.save()

    return redirect('cart_view')


from django.db import models
from django.contrib.auth.models import User
from .models import Product

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)  # Store size as a string (e.g., '5', '6', etc.)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} ({self.size}) - Quantity: {self.quantity}"

    # Optional: You can add additional logic for total price calculation
    def total_price(self):
        return self.quantity * self.product.price

        


<div class="cart-item">
    {% for item in cart_items %}
        <div class="cart-product">
            <p>{{ item.product.name }}</p>
            <p>Size: {{ item.size }}</p>
            <p>Quantity: {{ item.quantity }}</p>
            <p>Price: {{ item.total_price }}</p>
        </div>
    {% endfor %}
</div>
