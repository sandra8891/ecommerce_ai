# models.py
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

class Gallery(models.Model):
    CATEGORY_CHOICES = [
        ('women', 'Women'),
        ('men', 'Men'),
        ('unisex', 'Unisex'),
    ]
    name = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    feedimage1 = models.ImageField(upload_to='gallery_images/', blank=True, null=True)
    feedimage2 = models.ImageField(upload_to='gallery_images/', blank=True, null=True)
    feedimage3 = models.ImageField(upload_to='gallery_images/', blank=True, null=True)
    feedimage4 = models.ImageField(upload_to='gallery_images/', blank=True, null=True)
    feedimage5 = models.ImageField(upload_to='gallery_images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='unisex')
    rating=models.FloatField(default=0)
    vector_data=models.TextField(null=True)
    
    def __str__(self):
        return self.name
    

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Gallery, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Gallery, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.user.username
    
    
class users(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vector_data=models.TextField(null=True)




class ViewHistory(models.Model):
    product=models.ForeignKey(Gallery,on_delete=models.CASCADE)
    user=models.ForeignKey(users,on_delete=models.CASCADE)
    
class SearchHistory(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(users, on_delete=models.CASCADE)
    
    
    
class reviews(models.Model):
    rating=models.IntegerField()
    description=models.TextField()
    uname=models.ForeignKey(users,on_delete=models.CASCADE)
    pname=models.ForeignKey(Gallery,on_delete=models.CASCADE)
     
    
    
    
    
    
    

class Order(models.Model):
    PAYMENT_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Gallery, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    address = models.TextField()
    place = models.CharField(max_length=100)
    email = models.EmailField()
    username = models.CharField(max_length=150, blank=True)  # Store username explicitly
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    provider_order_id = models.CharField(max_length=40, blank=True, null=True)
    payment_id = models.CharField(max_length=36, blank=True, null=True)
    signature_id = models.CharField(max_length=128, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = self.product.price * self.quantity
        if not self.username:
            self.username = self.user.username
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} by {self.username}"
    
    

