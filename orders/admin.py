from django.contrib import admin
from .models import Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer_id', 'order_status', 'payment_status', 
                    'order_total', 'created_at']
    list_filter = ['order_status', 'payment_status', 'created_at']
    search_fields = ['order_id', 'customer_id', 'customer_email']
    readonly_fields = ['order_id', 'created_at', 'updated_at', 'totals_signature']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order_item_id', 'order', 'product_name', 'quantity', 
                    'unit_price', 'line_total']
    search_fields = ['product_name', 'sku']
    readonly_fields = ['order_item_id', 'created_at']