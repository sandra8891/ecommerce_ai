from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime, timedelta
from .models import *
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Gallery, Cart, Wishlist
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from .vectorize import vectorize_product_with_reviews,vectorize_user_with_search,pd
import razorpay
import json
from .read_content import *
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import pandas as pd
from sentence_transformers import SentenceTransformer
from django.db.models import Q
from django.db.models import Case, When
import numpy as np
import torch
import logging





def getuser(request):
    return request.session.get('user')


def filter_price(data, price):
    price2 = []
    for i in data:
        for j in price:
            if i.pk == j.product.pk:
                price2.append(j)
                break
    return price2


# def types(request):
#     type2 = []
#     for i in Gallery.objects.all():
#         if i.category and i.category.name not in type2:
#             type2.append(i.category.name)
#     return type2





def gallery(request):
    if request.method == 'POST':

        # Get form data
        myimage1 = request.FILES.get('feedimage1')
        myimage2 = request.FILES.get('feedimage2')
        myimage3 = request.FILES.get('feedimage3')
        myimage4 = request.FILES.get('feedimage4')
        myimage5 = request.FILES.get('feedimage5')
        name = request.POST.get("todo")
        price = request.POST.get("date")
        quantity = request.POST.get("quantity")
        model_type = request.POST.get("model")
        description = request.POST.get("description")
        category = request.POST.get("category")

        # Basic validation
        if not name or not price or not quantity or not model_type or not category:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "galleryupload.html")

        # Create and save the gallery object
        obj = Gallery(
            name=name,
            model=model_type,
            quantity=quantity,
            price=price,
            feedimage1=myimage1,
            feedimage2=myimage2,
            feedimage3=myimage3,
            feedimage4=myimage4,
            feedimage5=myimage5,
            description=description,
            user=request.user,
            category=category
        )
        obj.save()

        df = pd.DataFrame([{
            "id": obj.id,
            "name": name,
            "rating": 0,
            "category": category,
            "description": description,
            "reviews": '',
        }])
        
        # Generate product vector
        product_vector = vectorize_product_with_reviews(df.iloc[0])
        print(product_vector)
        obj.vector_data = json.dumps(product_vector[0].tolist())
        obj.save()
    return render(request, "galleryupload.html")



def usersignup(request):
    if request.POST:
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')

        
        if not username or not email or not password or not confirmpassword:
            messages.error(request, 'All fields are required.')
        elif confirmpassword != password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
        
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            dt= users.objects.create(user=user)
            dt.save()
            user_datas = [{
                "user_id": user.id,
                "product":'',
                "search": ''
            }]
            df=pd.DataFrame(user_datas)
            user_vectors = vectorize_user_with_search(df)
            # print('User vector in register',user_vectors)
            dt.vector_data = json.dumps(user_vectors[0].tolist())
            dt.save()
            messages.success(request, "Account created successfully!")
            return redirect('loginuser')  

    return render(request, "signup.html")

def loginuser(request):
    if request.user.is_authenticated:
        return redirect('firstpage')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            request.session['username'] = username
            if  user.is_superuser:
                return redirect('adminindex')
            else:
                return redirect('firstpage')
        else:
            messages.error(request, "Invalid credentials.")
    
    return render(request, 'login.html')

def adminindex(request):
    if not request.user.is_authenticated:
        messages.error(request, "You need to be logged in to access this page.")
        return redirect('loginuser')

    gallery_images = Gallery.objects.all()  # Fetch all gallery items
    return render(request, 'adminindex.html', {"gallery_images": gallery_images})

from django.contrib.auth.models import User
from django.shortcuts import render, redirect

def admin_users(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginuser')

    # Exclude superusers (admin accounts)
    users = User.objects.filter(is_superuser=False)
    return render(request, 'admin_users.html', {'users': users})



# def firstpage(request): 
#     gallery_images = Gallery.objects.all()  
#     if request.user.is_authenticated:
#         cart_item_count = Cart.objects.filter(user=request.user).count()
#         wishlist_item_count = Wishlist.objects.filter(user=request.user).count() 
#     else:
#         cart_item_count = 0 
#         wishlist_item_count = 0
#     return render(request, "userindex.html", {
#         "gallery_images": gallery_images,
#         "cart_item_count": cart_item_count,
#         "wishlist_item_count": wishlist_item_count,
        
#     })
def firstpage(request):
    # Fetch all required Gallery objects in one query
    all_products = Gallery.objects.select_related('user').all()

    # Prepare product vectors and IDs for recommendations
    product_ids = []
    product_vectors = []
    for product in all_products:
        if product.vector_data:
            try:
                vector = json.loads(product.vector_data)
                product_ids.append(product.pk)
                product_vectors.append(vector)
            except json.JSONDecodeError:
                logger.warning(f"Invalid vector_data for Gallery ID {product.pk}")
                continue

    # Convert to tensor
    product_vectors = torch.tensor(product_vectors, dtype=torch.float32) if product_vectors else torch.tensor([], dtype=torch.float32)

    # Initialize recommended products
    recommended_products = []

    # Generate recommendations for authenticated user
    if request.user.is_authenticated:
        try:
            user_obj = users.objects.select_related('user').get(user=request.user)
            if user_obj.vector_data:
                user_vector = torch.tensor(json.loads(user_obj.vector_data), dtype=torch.float32)
                if product_vectors.numel() > 0:
                    recommended = recommend_product(user_vector, product_vectors, product_ids, top_n=4)
                    product_pks = [rec[0] for rec in recommended]
                    preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(product_pks)])
                    recommended_products = all_products.filter(pk__in=product_pks).order_by(preserved_order)
        except users.DoesNotExist:
            logger.info(f"No user profile for {request.user.username}")
        except json.JSONDecodeError:
            logger.warning(f"Invalid vector_data for user {request.user.username}")
        except Exception as e:
            logger.error(f"Recommendation error for user {request.user.username}: {str(e)}")

    # Fallback to random products if no recommendations
    if not recommended_products:
        recommended_products = all_products.order_by('?')[:4]

    # Get new arrivals (limit to 10 for consistency with template)
    gallery_images = all_products.order_by('-id')[:10]

    # Cart and wishlist counts
    cart_item_count = Cart.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
    wishlist_item_count = Wishlist.objects.filter(user=request.user).count() if request.user.is_authenticated else 0

    return render(request, "userindex.html", {
        'gallery_images': gallery_images,
        'products': recommended_products,  # Match template variable
        'cart_item_count': cart_item_count,
        'wishlist_item_count': wishlist_item_count,
    })






def verifyotp(request):
    if request.POST:
        otp = request.POST.get('otp')
        otp1 = request.session.get('otp')
        otp_time_str = request.session.get('otp_time') 

    
        if otp_time_str:
            otp_time = datetime.fromisoformat(otp_time_str)
            otp_expiry_time = otp_time + timedelta(minutes=5)
            if datetime.now() > otp_expiry_time:
                messages.error(request, 'OTP has expired. Please request a new one.')
                del request.session['otp']
                del request.session['otp_time']
                return redirect('verifyotp')

        if otp == otp1:
            del request.session['otp']
            del request.session['otp_time']
            return redirect('passwordreset')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    
    otp = ''.join(random.choices('123456789', k=6))
    request.session['otp'] = otp
    request.session['otp_time'] = datetime.now().isoformat()
    message = f'Your email verification code is: {otp}'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [request.session.get('email')]
    send_mail('Email Verification', message, email_from, recipient_list)

    return render(request, "otp.html")

def delete_g(request, id):
    feeds = Gallery.objects.filter(pk=id)
    feeds.delete()
    return redirect('adminindex')

def edit_g(request, pk):
    gallery_item = Gallery.objects.filter(pk=pk).first()

    if not gallery_item:
        messages.error(request, "Gallery item not found.")
        return redirect('adminindex')

    if request.method == "POST":
        edit1 = request.POST.get('todo')
        edit2 = request.POST.get('model')
        edit3 = request.POST.get('date')
        edit4 = request.POST.get('quantity')
        edit5 = request.POST.get('description')
        category = request.POST.get('category')

        gallery_item.name = edit1
        gallery_item.model = edit2
        gallery_item.price = edit3
        gallery_item.quantity = edit4
        gallery_item.description = edit5
        gallery_item.category = category

        # Update images if new ones are uploaded
        if 'feedimage1' in request.FILES:
            gallery_item.feedimage1 = request.FILES['feedimage1']
        if 'feedimage2' in request.FILES:
            gallery_item.feedimage2 = request.FILES['feedimage2']
        if 'feedimage3' in request.FILES:
            gallery_item.feedimage3 = request.FILES['feedimage3']
        if 'feedimage4' in request.FILES:
            gallery_item.feedimage4 = request.FILES['feedimage4']
        if 'feedimage5' in request.FILES:
            gallery_item.feedimage5 = request.FILES['feedimage5']

        gallery_item.save()

        messages.success(request, "Gallery item updated successfully.")
        return redirect('adminindex')

    else:
        return render(request, 'edit_gallery.html', {'data': gallery_item})

def getusername(request):
    if request.POST:
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            request.session['email'] = user.email
            return redirect('verifyotp')
        except User.DoesNotExist:
            messages.error(request, "Username does not exist.")
            return redirect('getusername')

    return render(request, 'getusername.html')


def passwordreset(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')

    
        if confirmpassword != password:
            messages.error(request, "Passwords do not match.")
        else:
            email = request.session.get('email')
            try:
                user = User.objects.get(email=email)

                user.set_password(password)
                user.save()

                del request.session['email']
                messages.success(request, "Your password has been reset successfully.")
                
                user = authenticate(username=user.username, password=password)
                if user is not None:
                    login(request, user)

                return redirect('loginuser')
            except User.DoesNotExist:
                messages.error(request, "No user found with that email address.")
                return redirect('getusername')

    return render(request, "passwordreset.html")





def products(request, id):
    gallery_image = get_object_or_404(Gallery, pk=id)  # Renamed to singular for clarity
    cart_item_count = 0
    gallery_image.in_cart = False

    if request.user.is_authenticated:
        cart_item_count = Cart.objects.filter(user=request.user).count()
        # Check if the product is in the user's cart
        gallery_image.in_cart = Cart.objects.filter(user=request.user, product=gallery_image).exists()

    user = request.user
    user_name, created = users.objects.get_or_create(user=user)

    # Save view history
    ViewHistory.objects.create(user=user_name, product=gallery_image)

    # Prepare view history data for vectorization
    existing_user_data = ViewHistory.objects.filter(user=user_name)
    existing_products = [history.product.name for history in existing_user_data]
    data = [{
        'user_id': user_name.id,
        'product': ','.join(existing_products),
        'search': ''
    }]
    df = pd.DataFrame(data)

    # Vectorize and save
    try:
        user_vectors = vectorize_user_with_search(df)
        user_name.vector_data = json.dumps(user_vectors[0].tolist())
        user_name.save()
    except Exception as e:
        print(f"Vectorization failed: {e}")

    # Fetch reviews
    rs = reviews.objects.filter(pname=gallery_image)
    isReviewed = reviews.objects.filter(uname=user_name, pname=gallery_image).exists()
    return render(request, 'products.html', {
        "gallery_image": gallery_image,  # Pass single object
        "cart_item_count": cart_item_count,
        'isReviewed': isReviewed,
        'reviews': rs,
        'product': gallery_image,  # Pass as product for rating context
    })


def add_to_cart(request, id):
    if not request.user.is_authenticated:
        messages.error(request, "You need to be logged in to add items to the cart.")
        return redirect('loginuser')  

    try:
        product = Gallery.objects.get(id=id)
    except Gallery.DoesNotExist:
        return redirect('product_not_found')  # Handle the case where the pr    oduct does not exist

    # Create or update the cart item
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
    )

    if not created:
        if cart_item.product.quantity > cart_item.quantity:
            cart_item.quantity += 1
        else:
            messages.error(request, "Out of stock.")
            return redirect('cart_view')  # Redirect to cart view if out of stock
    else:
        cart_item.quantity = 1
        cart_item.save()

    return redirect('cart_view')  # Redirect to cart view after adding the item
@login_required
def increment_cart(request, id):
    cart_item = get_object_or_404(Cart, pk=id, user=request.user)
    if cart_item.product.quantity > cart_item.quantity:
        cart_item.quantity += 1
        cart_item.save()
    else:
        messages.error(request, "Not enough stock available.")

    return redirect('cart_view')


@login_required
def decrement_cart(request, id):
    cart_item = get_object_or_404(Cart, pk=id, user=request.user)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart_view')

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    cart_item_count = cart_items.count()
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price, 'cart_item_count': cart_item_count})


@login_required
def delete_cart(request, id):
    cart_item = get_object_or_404(Cart, pk=id, user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart_view')


@login_required
def add_to_wishlist(request, id):
    # Get the product from the Gallery model
    product = get_object_or_404(Gallery, id=id)
    
    # Check if the product is already in the user's wishlist
    if not Wishlist.objects.filter(user=request.user, product=product).exists():
        # Add the product to the wishlist
        wishlist_item = Wishlist(user=request.user, product=product)
        wishlist_item.save()
        messages.success(request, f'{product.name} added to your wishlist!')
    else:
        messages.info(request, f'{product.name} is already in your wishlist.')
    
    return redirect('wishlist_view')

@login_required
def wishlist_view(request):
    # Get all the products in the user's wishlist
    wishlist_items = Wishlist.objects.filter(user=request.user)
    
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def remove_from_wishlist(request, id):
    # Get the product object
    product = get_object_or_404(Gallery, id=id)
    
    # Find the wishlist entry for the user and the product
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product)
    
    # If it exists, delete the item
    if wishlist_item.exists():
        wishlist_item.delete()
        messages.success(request, f'{product.name} has been removed from your wishlist.')
    else:
        messages.info(request, f'{product.name} is not in your wishlist.')
    
    # Redirect back to the wishlist view page
    return redirect('wishlist_view')


# def search_results(request):
#     query = request.GET.get('q')  
#     results = None  
#     if query:
#         results = Gallery.objects.filter(
#             name__icontains=query
#         ) | Gallery.objects.filter(
#             model__icontains=query
#         )
    
#     return render(request, 'search_results.html', {'results': results, 'query': query})




def types(request):
    return list(Gallery.objects.values_list('category', flat=True).distinct())

def search_func(request):
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        if not query:
            return redirect('firstpage')  # Redirect if query is empty

        # Initialize context
        context = {
            'query': query,
            'results': [],  # Match template variable
            'cart_item_count': 0,
            'wishlist_item_count': 0,
        }

        # Handle authenticated user
        if request.user.is_authenticated:
            try:
                user_obj = users.objects.get(user=request.user)  # Use user field, not name
                # Save search query
                SearchHistory.objects.create(query=query, user=user_obj)

                # Get user search and view history
                user_search = [s.query for s in SearchHistory.objects.filter(user=user_obj)]
                user_products = [p.product.name for p in ViewHistory.objects.filter(user=user_obj)]

                # Prepare data for vectorization
                user_data = [{
                    'user_id': request.user.id,
                    'product': ','.join(user_products) if user_products else '',
                    'search': ','.join(user_search) if user_search else ''
                }]
                df = pd.DataFrame(user_data)

                # Update user vector
                user_vectors = vectorize_user_with_search(df)
                user_obj.vector_data = json.dumps(user_vectors[0].tolist())
                user_obj.save()

                # Cart and wishlist counts
                context['cart_item_count'] = Cart.objects.filter(user=request.user).count()
                context['wishlist_item_count'] = Wishlist.objects.filter(user=request.user).count()
            except users.DoesNotExist:
                logger.info(f"No user profile for {request.user.username}")

        # Search products by name or category
        results = Gallery.objects.filter(
            Q(name__icontains=query) | Q(category__icontains=query)
        ).distinct()

        # Optional: Enhance with vector-based search
        if results and request.user.is_authenticated and user_obj.vector_data:
            try:
                user_vector = torch.tensor(json.loads(user_obj.vector_data), dtype=torch.float32)
                product_ids = []
                product_vectors = []
                for product in results:
                    if product.vector_data:
                        try:
                            vector = json.loads(product.vector_data)
                            product_ids.append(product.pk)
                            product_vectors.append(vector)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid vector_data for Gallery ID {product.pk}")
                            continue

                if product_vectors:
                    product_vectors = torch.tensor(product_vectors, dtype=torch.float32)
                    similarities = util.cos_sim(user_vector, product_vectors)
                    similarity_scores = similarities[0].cpu().numpy()
                    sorted_indices = np.argsort(similarity_scores)[::-1]
                    top_n = min(10, len(product_ids))  # Limit to 10 results
                    top_product_ids = [product_ids[idx] for idx in sorted_indices[:top_n]]
                    preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(top_product_ids)])
                    results = results.filter(pk__in=top_product_ids).order_by(preserved_order)
            except Exception as e:
                logger.error(f"Vector search error for user {request.user.username}: {str(e)}")

        context['results'] = results
        context['category'] = types(request)

        return render(request, 'search_results.html', context)

    return redirect('firstpage')  # Redirect for non-GET requests


@login_required
def myprofile(request):
    # If the user submits the form to update profile
    if request.method == "POST":
        new_email = request.POST.get('email')
        new_username = request.POST.get('username')
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confpassword')
        new_address = request.POST.get('address')
        new_place = request.POST.get('place')
        new_phone_number = request.POST.get('phone_number')

        user = request.user

        # Check for changes in user information
        if new_email != user.email:
            if User.objects.filter(email=new_email).exists():
                messages.error(request, "This email is already taken.")
                return redirect('myprofile')
            user.email = new_email

        if new_username != user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, "This username is already taken.")
                return redirect('myprofile')
            user.username = new_username

        if new_password and new_password == confirm_password:
            user.set_password(new_password)
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('myprofile')

        # Save changes
        user.save()

        # Update or create the user profile
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        user_profile.address = new_address
        user_profile.place = new_place
        user_profile.phone_number = new_phone_number
        user_profile.save()

        # Re-authenticate the user after changing password
        if new_password:
            messages.success(request, "Your profile has been updated. Please log in again.")
            logout(request)
            return redirect('loginuser')

        messages.success(request, "Your profile has been updated.")
        return redirect('myprofile')  # Redirect to the same page to see the changes

    # Display the user's current profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    return render(request, 'myprofile.html', {'user_profile': user_profile})





def about_us(request):
    return render(request,'aboutus.html')
def home(request):
    return render(request,'userindex.html')

def logoutuser(request):
    logout(request) 
    request.session.flush() 
    return redirect('loginuser') 


def logoutadmin(request):
    logout(request)
    request.session.flush()
    return redirect('firstpage')


def new_arrivals_page(request):
    gallery_images = Gallery.objects.all().order_by('-id')  # or use a 'created_at' field if available
    return render(request, 'new_arrivals_page.html', {'gallery_images': gallery_images})



def category_products(request, category):
    gallery_images = Gallery.objects.filter(category=category)
    if request.user.is_authenticated:
        cart_item_count = Cart.objects.filter(user=request.user).count()
        wishlist_item_count = Wishlist.objects.filter(user=request.user).count()
    else:
        cart_item_count = 0
        wishlist_item_count = 0
    return render(request, "category_products.html", {
        "gallery_images": gallery_images,
        "cart_item_count": cart_item_count,
        "wishlist_item_count": wishlist_item_count,
        "category": category.capitalize()
    })
    
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Cart, UserProfile, Order
import razorpay
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    user_profile = UserProfile.objects.filter(user=request.user).first()

    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart_view')

    # Calculate total price and item totals
    total_price = sum(Decimal(item.product.price) * item.quantity for item in cart_items)
    for item in cart_items:
        item.total = Decimal(item.product.price) * item.quantity  # Add total for each item

    if request.method == "POST":
        address = request.POST.get('address')
        place = request.POST.get('place')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        payment_method = request.POST.get('payment_method')

        # Validate input
        if not all([address, place, email, payment_method]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'checkout.html', {
                'cart_items': cart_items,
                'total_price': total_price,
                'user_profile': user_profile,
            })

        # Check stock availability
        for item in cart_items:
            if item.product.quantity < item.quantity:
                messages.error(request, f"Insufficient stock for {item.product.name}.")
                return render(request, 'checkout.html', {
                    'cart_items': cart_items,
                    'total_price': total_price,
                    'user_profile': user_profile,
                })

        # Validate total_price
        max_amount = Decimal('100000')
        if total_price <= 0:
            messages.error(request, "Order amount cannot be zero or negative.")
            return render(request, 'checkout.html', {
                'cart_items': cart_items,
                'total_price': total_price,
                'user_profile': user_profile,
            })
        if total_price > max_amount:
            messages.error(request, f"Order amount exceeds maximum limit of {max_amount} INR.")
            return render(request, 'checkout.html', {
                'cart_items': cart_items,
                'total_price': total_price,
                'user_profile': user_profile,
            })

        # Create orders
        orders = []
        for item in cart_items:
            order = Order.objects.create(
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                address=address,
                place=place,
                email=email,
                phone_number=phone_number,
                payment_method=payment_method,
                total_amount=Decimal(item.product.price) * item.quantity,
                username=request.user.username
            )
            orders.append(order)

        if payment_method == 'ONLINE':
            client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
            razorpay_order = client.order.create({
                'amount': int(total_price * 100),
                'currency': 'INR',
                'payment_capture': '1'
            })

            # Update all orders with the same provider_order_id
            for order in orders:
                order.provider_order_id = razorpay_order['id']
                order.save()

            # Store order and cart item IDs in session
            request.session['checkout_order_ids'] = [order.id for order in orders]
            request.session['cart_item_ids'] = [item.id for item in cart_items]

            callback_url = request.build_absolute_uri(reverse('razorpay_callback'))
            return render(request, 'payment.html', {
                'order': orders[0],
                'razorpay_key': settings.RAZOR_KEY_ID,
                'razorpay_order_id': razorpay_order['id'],
                'amount': int(total_price * 100),
                'currency': 'INR',
                'callback_url': callback_url,
                'name': request.user.username,
                'description': f'Payment for multiple orders',
                'prefill': {
                    'name': request.user.username,
                    'email': email,
                    'contact': phone_number or '',
                }
            })

        # For COD: Update stock, clear cart, and redirect
        for item in cart_items:
            item.product.quantity -= item.quantity
            item.product.save()
        cart_items.delete()
        messages.success(request, "Order placed successfully!")
        return redirect('my_orders')

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'user_profile': user_profile,
    })

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Gallery, id=product_id)
    user_profile = UserProfile.objects.filter(user=request.user).first()
    quantity = 1  # Default quantity to 1

    if product.quantity < quantity:
        messages.error(request, f"Only {product.quantity} units available.")
        return redirect('products', id=product_id)

    if request.method == "POST":
        address = request.POST.get('address')
        place = request.POST.get('place')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        payment_method = request.POST.get('payment_method')

        # Validate input
        if not all([address, place, email, payment_method]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'buy_now.html', {
                'product': product,
                'quantity': quantity,
                'user_profile': user_profile,
            })

        total_amount = Decimal(product.price) * quantity

        # Create order
        order = Order.objects.create(
            user=request.user,
            product=product,
            quantity=quantity,
            address=address,
            place=place,
            email=email,
            phone_number=phone_number,
            payment_method=payment_method,
            total_amount=total_amount,
            username=request.user.username
        )

        if payment_method == 'ONLINE':
            client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
            razorpay_order = client.order.create({
                'amount': int(total_amount * 100),
                'currency': 'INR',
                'payment_capture': '1'
            })

            order.provider_order_id = razorpay_order['id']
            order.save()

            callback_url = request.build_absolute_uri(reverse('razorpay_callback'))
            return render(request, 'payment.html', {
                'order': order,
                'razorpay_key': settings.RAZOR_KEY_ID,
                'razorpay_order_id': razorpay_order['id'],
                'amount': int(total_amount * 100),
                'currency': 'INR',
                'callback_url': callback_url,
                'name': request.user.username,
                'description': f'Payment for order {order.id}',
                'prefill': {
                    'name': request.user.username,
                    'email': email,
                    'contact': phone_number or '',
                }
            })

        # For COD: Update stock and redirect
        product.quantity -= quantity
        product.save()
        messages.success(request, "Order placed successfully!")
        return redirect('my_orders')

    context = {
        'product': product,
        'quantity': quantity,
        'user_profile': user_profile,
    }
    return render(request, 'buy_now.html', context)


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate total price for each order
    for order in orders:
        order.total_price = order.quantity * order.product.price
    
    return render(request, 'my_orders.html', {'orders': orders})





@staff_member_required
def admin_orders(request):
    orders = Order.objects.all()
    for order in orders:
        order.total_price = order.quantity * order.product.price
    return render(request, 'admin_orders.html', {'orders': orders})


@staff_member_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == "POST":
        new_status = request.POST.get('status')
        print(f"Order ID: {order_id}, New Status: {new_status}, Order Email: {order.email}, User Email: {order.user.email}")
        if new_status in dict(Order.STATUS_CHOICES).keys():
            if order.status == new_status:
                messages.info(request, "Order status is already set to this value.")
                return redirect('admin_orders')
                
            old_status = order.status
            order.status = new_status
            order.save()

            # Use order.email or fallback to user.email
            recipient_email = order.email or order.user.email
            if not recipient_email:
                logger.warning(f"No email address provided for order {order.id} (User: {order.user.username})")
                messages.warning(request, f"Order status updated to {new_status}, but no email address found.")
                return redirect('admin_orders')

            # Send email notification
            subject = f'Order {order.id} Status Update'
            message = (
                f'Dear {order.user.username},\n\n'
                f'The status of your order (ID: {order.id}) for {order.product.name} has been updated.\n'
                f'Previous Status: {dict(Order.STATUS_CHOICES).get(old_status)}\n'
                f'New Status: {dict(Order.STATUS_CHOICES).get(new_status)}\n\n'
                f'Thank you for shopping with CrocsHub!'
            )
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [recipient_email]
            print(f"Sending email to: {recipient_list}, Subject: {subject}")
            
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=email_from,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
                messages.success(request, f"Order status updated to {new_status} and email sent to {recipient_email}.")
            except Exception as e:
                logger.error(f"Failed to send email for order {order.id} to {recipient_email}: {str(e)}")
                print(f"Email error: {str(e)}")
                error_message = "Order status updated, but email could not be sent. "
                if "535" in str(e):
                    error_message += "Check your Gmail SMTP credentials (username/password or App Password)."
                else:
                    error_message += f"Error: {str(e)}"
                messages.warning(request, error_message)
        else:
            messages.error(request, "Invalid status selected.")
    
    return redirect('admin_orders')





#######razorpay#######

@login_required
def order_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

    # Calculate total amount (product price * quantity)
    total_amount = order.product.price * order.quantity

    # Create Razorpay order
    razorpay_order = client.order.create({
        'amount': int(total_amount * 100),  # Amount in paise
        'currency': 'INR',
        'payment_capture': '1'  # Auto-capture payment
    })

    # Save Razorpay order ID to the order
    order.provider_order_id = razorpay_order['id']
    order.save()

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse('razorpay_callback'))

    return render(request, 'payment.html', {
        'order': order,
        'razorpay_key': settings.RAZOR_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'amount': int(total_amount * 100),
        'currency': 'INR',
        'callback_url': callback_url,
        'name': order.user.username,
        'description': f'Payment for order {order.id}',
        'prefill': {
            'name': order.user.username,
            'email': order.email,
            'contact': '',  # Add phone number if available in UserProfile
        }
    })
    
    
@csrf_exempt
def razorpay_callback(request):
    client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

    if "razorpay_signature" in request.POST:
        payment_id = request.POST.get('razorpay_payment_id', '')
        provider_order_id = request.POST.get('razorpay_order_id', '')
        signature_id = request.POST.get('razorpay_signature', '')

        try:
            orders = Order.objects.filter(provider_order_id=provider_order_id)
            if not orders:
                messages.error(request, 'Order not found.')
                return redirect('my_orders')

            params_dict = {
                'razorpay_order_id': provider_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature_id
            }
            if client.utility.verify_payment_signature(params_dict):
                for order in orders:
                    order.payment_id = payment_id
                    order.signature_id = signature_id
                    order.status = 'PENDING'
                    order.product.quantity -= order.quantity
                    order.product.save()
                    order.save()
                # Clear cart if applicable
                if 'checkout_order_ids' in request.session:
                    Cart.objects.filter(id__in=request.session.get('cart_item_ids', [])).delete()
                    del request.session['checkout_order_ids']
                    del request.session['cart_item_ids']
                messages.success(request, 'Payment successful! Your orders are confirmed.')
            else:
                for order in orders:
                    order.status = 'FAILED'
                    order.save()
                messages.error(request, 'Payment verification failed.')
            return redirect('my_orders')

        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('my_orders')

    else:
        error_metadata = json.loads(request.POST.get('error[metadata]', '{}'))
        provider_order_id = error_metadata.get('order_id', '')

        try:
            orders = Order.objects.filter(provider_order_id=provider_order_id)
            for order in orders:
                order.status = 'FAILED'
                order.save()
            messages.error(request, 'Payment failed. Please try again.')
            return redirect('my_orders')

        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('my_orders')
        
        
        
        
# @login_required
# def addReview(request, pk):
#     try:
#         prod = Gallery.objects.get(pk=pk)
#     except Gallery.DoesNotExist:
#         messages.error(request, "Product not found.")
#         return redirect('firstpage')

#     if request.method == 'POST':
#         rating = request.POST.get('rating')
#         description = request.POST.get('description')

#         # Validate inputs
#         if not rating or not description:
#             messages.error(request, "Rating and description are required.")
#             return redirect(reverse('products', args=[pk]))

#         try:
#             rating = int(rating)
#             if rating < 1 or rating > 5:
#                 raise ValueError
#         except ValueError:
#             messages.error(request, "Invalid rating. Please select a rating between 1 and 5.")
#             return redirect(reverse('products', args=[pk]))

#         try:
#             user_profile = users.objects.get(user=request.user)
#         except users.DoesNotExist:
#             messages.error(request, "User profile not found. Please contact support.")
#             return redirect('userlogin')

#         # Check for existing review
#         if reviews.objects.filter(uname=user_profile, pname=prod).exists():
#             messages.error(request, "You have already reviewed this product.")
#             return redirect(reverse('products', args=[pk]))

#         # Create and save review
#         data = reviews.objects.create(
#             rating=rating,
#             description=description,
#             uname=user_profile,
#             pname=prod
#         )
#         data.save()

#         # Update product rating
#         rev = reviews.objects.filter(pname=prod)
#         total = [i.rating for i in rev]
#         if total:
#             total_rating = round(sum(total) / len(total), 1)
#             prod.rating = total_rating
#         else:
#             prod.rating = rating
#         prod.save()

#         # Vectorize product with reviews
#         comments = [i.description for i in rev]
#         pro_data = [{
#             "pro_id": prod.id,
#             "name": prod.name,
#             "rating": prod.rating,
#             "model": getattr(prod, 'model', ''),
#             "reviews": ','.join(comments)
#         }]
#         df = pd.DataFrame(pro_data)
#         try:
#             product_vector = vectorize_product_with_reviews(df)
#             prod.vector_data = json.dumps(product_vector[0].tolist())
#             prod.save()
#         except Exception as e:
#             print(f"Vectorization failed: {e}")
#             messages.warning(request, "Review saved, but vectorization failed. Contact support.")

#         messages.success(request, "Review submitted successfully!")
#         return redirect(reverse('products', args=[pk]))  # Updated to 'products'
#     else:
#         reviews_list = reviews.objects.filter(pname=prod)
#         cart_items = Cart.objects.filter(user=request.user)
#         cart_product_ids = [item.product.id for item in cart_items]
#         isReviewed = reviews.objects.filter(uname__user=request.user, pname=prod).exists()
#         context = {
#             'gallery_images': [prod],
#             'reviews': reviews_list,
#             'cart_product_ids': cart_product_ids,
#             'isReviewed': isReviewed
#         }
#         return render(request, 'products.html', context)


logger = logging.getLogger(__name__)

@login_required
def addReview(request, pk):
    try:
        prod = get_object_or_404(Gallery, pk=pk)
    except Gallery.DoesNotExist:
        messages.error(request, "Product not found.")
        return redirect('firstpage')

    if request.method == 'POST':
        rating = request.POST.get('rating')
        description = request.POST.get('description')

        # Validate inputs
        if not rating or not description:
            messages.error(request, "Rating and description are required.")
            return redirect(reverse('products', args=[pk]))

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, "Invalid rating. Please select a rating between 1 and 5.")
            return redirect(reverse('products', args=[pk]))

        # Get or create user profile
        try:
            user_profile = users.objects.get(user=request.user)
        except users.DoesNotExist:
            messages.error(request, "User profile not found. Please contact support.")
            return redirect('loginuser')

        # Check for existing review
        if reviews.objects.filter(uname=user_profile, pname=prod).exists():
            messages.error(request, "You have already reviewed this product.")
            return redirect(reverse('products', args=[pk]))

        # Create and save review
        data = reviews.objects.create(
            rating=rating,
            description=description,
            uname=user_profile,  # Associate with user_profile
            pname=prod
        )
        data.save()

        # Update product rating
        rev = reviews.objects.filter(pname=prod)
        total = [i.rating for i in rev]
        if total:
            total_rating = round(sum(total) / len(total), 1)
            prod.rating = total_rating
        else:
            prod.rating = rating
        prod.save()

        # Vectorize product with reviews
        comments = [i.description for i in rev]
        pro_data = [{
            "pro_id": prod.id,
            "name": prod.name,
            "rating": prod.rating,
            "model": getattr(prod, 'model', ''),
            "reviews": ','.join(comments)
        }]
        df = pd.DataFrame(pro_data)
        try:
            product_vector = vectorize_product_with_reviews(df)
            prod.vector_data = json.dumps(product_vector[0].tolist())
            prod.save()
        except Exception as e:
            logger.error(f"Vectorization failed: {e}")
            messages.warning(request, "Review saved, but vectorization failed. Contact support.")

        messages.success(request, "Review submitted successfully!")
        return redirect(reverse('products', args=[pk]))

    # GET request: Display the product and reviews
    reviews_list = reviews.objects.filter(pname=prod)
    cart_items = Cart.objects.filter(user=request.user)
    cart_product_ids = [item.product.id for item in cart_items]
    isReviewed = reviews.objects.filter(uname__user=request.user, pname=prod).exists()
    context = {
        'gallery_image': prod,  # Changed to singular for consistency
        'reviews': reviews_list,
        'cart_product_ids': cart_product_ids,
        'isReviewed': isReviewed,
        'cart_item_count': cart_items.count(),
    }
    return render(request, 'products.html', context)



       
        
        
        
        
# @login_required
# def order_pay(request, order_id):
#     order = get_object_or_404(Order, id=order_id)
#     client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

#     # Use total_amount from Order model
#     total_amount = order.total_amount

#     # Validate total_amount
#     max_amount = 100000  # 100,000 INR
#     if total_amount <= 0:
#         messages.error(request, "Order amount cannot be zero or negative.")
#         return redirect('my_orders')
#     if total_amount > max_amount:
#         messages.error(request, f"Order amount exceeds maximum limit of {max_amount} INR.")
#         return redirect('my_orders')

#     # Create Razorpay order
#     razorpay_order = client.order.create({
#         'amount': int(total_amount * 100),  # Amount in paise
#         'currency': 'INR',
#         'payment_capture': '1'
#     })

#     # Save Razorpay order ID
#     order.provider_order_id = razorpay_order['id']
#     order.save()

#     # Build callback URL
#     callback_url = request.build_absolute_uri(reverse('razorpay_callback'))

#     return render(request, 'payment.html', {
#         'order': order,
#         'razorpay_key': settings.RAZOR_KEY_ID,
#         'razorpay_order_id': razorpay_order['id'],
#         'amount': int(total_amount * 100),
#         'currency': 'INR',
#         'callback_url': callback_url,
#         'name': order.user.username,
#         'description': f'Payment for order {order.id}',
#         'prefill': {
#             'name': order.user.username,
#             'email': order.email,
#             'contact': '',  # Add phone number if available
#         }
#     })

# @csrf_exempt
# def razorpay_call(request):
#     client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

#     if "razorpay_signature" in request.POST:
#         payment_id = request.POST.get('razorpay_payment_id', '')
#         provider_order_id = request.POST.get('razorpay_order_id', '')
#         signature_id = request.POST.get('razorpay_signature', '')

#         try:
#             orders = Order.objects.filter(provider_order_id=provider_order_id)
#             if not orders:
#                 messages.error(request, 'Order not found.')
#                 return redirect('my_orders')

#             params_dict = {
#                 'razorpay_order_id': provider_order_id,
#                 'razorpay_payment_id': payment_id,
#                 'razorpay_signature': signature_id
#             }
#             if client.utility.verify_payment_signature(params_dict):
#                 for order in orders:
#                     order.payment_id = payment_id
#                     order.signature_id = signature_id
#                     order.status = 'PENDING'
#                     # Update product stock only on successful payment
#                     order.product.quantity -= Decimal(order.quantity)
#                     order.product.save()
#                     order.save()
#                 # Clear cart if order IDs match session
#                 if 'checkout_order_ids' in request.session:
#                     Cart.objects.filter(id__in=request.session.get('cart_item_ids', [])).delete()
#                     del request.session['checkout_order_ids']
#                     del request.session['cart_item_ids']
#                 messages.success(request, 'Payment successful! Your orders are confirmed.')
#             else:
#                 for order in orders:
#                     order.status = 'FAILED'
#                     order.save()
#                 messages.error(request, 'Payment verification failed.')
#             return redirect('my_orders')

#         except Order.DoesNotExist:
#             messages.error(request, 'Order not found.')
#             return redirect('my_orders')

#     else:
#         # Handle failed payment
#         error_metadata = json.loads(request.POST.get('error[metadata]', '{}'))
#         provider_order_id = error_metadata.get('order_id', '')

#         try:
#             orders = Order.objects.filter(provider_order_id=provider_order_id)
#             for order in orders:
#                 order.status = 'FAILED'
#                 order.save()
#             messages.error(request, 'Payment failed. Please try again.')
#             return redirect('my_orders')

#         except Order.DoesNotExist:
#             messages.error(request, 'Order not found.')
#             return redirect('my_orders')