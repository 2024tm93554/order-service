from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
import uuid
import hashlib
import json


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('DELIVERED', 'Delivered'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
        ('FAILED', 'Failed'),
    ]

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.IntegerField()
    customer_name = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(blank=True)

    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('10.00'))
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    totals_signature = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_id} - {self.order_status}"

    def calculate_totals(self):
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.tax = (self.subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
        self.order_total = self.subtotal + self.tax + self.shipping
        self.generate_signature()

    def generate_signature(self):
        data = {
            'subtotal': str(self.subtotal),
            'tax': str(self.tax),
            'shipping': str(self.shipping),
            'total': str(self.order_total)
        }
        self.totals_signature = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()


class OrderItem(models.Model):
    order_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)

    product_id = models.IntegerField()
    sku = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255)

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),      # ← NEW: default value
        editable=False                # ← optional but clean
    )

    reservation_id = models.CharField(max_length=255, blank=True, null=True)
    warehouse = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def calculate_line_total(self):
        """Calculate line total and round to 2 decimals."""
        self.line_total = (self.unit_price * self.quantity).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        """Always keep line_total in sync."""
        self.calculate_line_total()
        super().save(*args, **kwargs)