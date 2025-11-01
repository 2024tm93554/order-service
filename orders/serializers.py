# orders/serializers.py
from decimal import Decimal
from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order_item_id', 'product_id', 'sku', 'product_name', 
                  'quantity', 'unit_price', 'line_total', 'reservation_id', 
                  'warehouse', 'created_at']
        read_only_fields = ['order_item_id', 'line_total', 'reservation_id', 
                           'warehouse', 'created_at']

class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    sku = serializers.CharField(max_length=100)
    quantity = serializers.IntegerField(min_value=1)

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['order_id', 'customer_id', 'customer_name', 'customer_email',
                  'order_status', 'payment_status', 'subtotal', 'tax', 
                  'shipping', 'order_total', 'idempotency_key', 
                  'totals_signature', 'created_at', 'updated_at', 'items']
        read_only_fields = ['order_id', 'subtotal', 'tax', 'order_total', 
                           'totals_signature', 'created_at', 'updated_at']

class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    items = OrderItemCreateSerializer(many=True)
    shipping = serializers.DecimalField(max_digits=10, decimal_places=2, 
                                       required=False, default=Decimal('10.00'))