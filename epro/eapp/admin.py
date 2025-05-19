from django.contrib import admin
from .models import Gallery

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'price', 'quantity')
    fields = ('name', 'model', 'price', 'quantity', 'feedimage1', 'feedimage2', 'feedimage3', 'feedimage4', 'feedimage5', 'description', 'user')