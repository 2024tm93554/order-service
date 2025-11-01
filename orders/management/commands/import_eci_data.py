from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from orders.models import Order, OrderItem
from orders.services import (MockCustomerService, MockCatalogService, 
                             MockInventoryService, CSVDataLoader)
import uuid

class Command(BaseCommand):
    help = 'Import ECI seed data from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing orders before importing',
        )

    def handle(self, *args, **options):
        self.stdout.write('='*70)
        self.stdout.write('IMPORTING ECI SEED DATA')
        self.stdout.write('='*70 + '\n')
        
        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing orders...')
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared\n'))
        
        # Load CSV data into mock services
        self.stdout.write('Loading CSV data into memory...')
        MockCustomerService.load_from_csv('eci_customers.csv')
        MockCatalogService.load_from_csv('eci_products.csv')
        MockInventoryService.load_from_csv('eci_inventory.csv')
        self.stdout.write(self.style.SUCCESS('✓ Loaded\n'))
        
        # Load orders and order_items
        orders_data = CSVDataLoader.load_csv_to_list('eci_orders.csv')
        order_items_data = CSVDataLoader.load_csv_to_list('eci_order_items.csv')
        
        if not orders_data:
            self.stdout.write(self.style.WARNING('No eci_orders.csv found!'))
            return
        
        # Group order items by order_id
        items_by_order = {}
        for item in order_items_data:
            order_id = str(item['order_id'])
            if order_id not in items_by_order:
                items_by_order[order_id] = []
            items_by_order[order_id].append(item)
        
        # Import orders with items
        self.stdout.write(f'Importing {len(orders_data)} orders...\n')
        imported = 0
        skipped = 0
        
        # Map CSV status to Django model status
        STATUS_MAP = {
            'CREATED': 'PENDING',
            'CANCELLED': 'CANCELLED',
            'DELIVERED': 'DELIVERED'
        }
        
        PAYMENT_MAP = {
            'SUCCESS': 'PAID',
            'FAILED': 'FAILED',
            'PENDING': 'UNPAID'
        }
        
        with transaction.atomic():
            for order_data in orders_data:
                try:
                    # Get customer info
                    customer_id = int(order_data['customer_id'])
                    customer = MockCustomerService.get_customer(customer_id)
                    
                    if not customer:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ Skipped order {order_data["order_id"]}: Customer {customer_id} not found'
                        ))
                        skipped += 1
                        continue
                    
                    # Map status from CSV to Django model
                    order_status = STATUS_MAP.get(order_data.get('order_status', 'CREATED'), 'PENDING')
                    payment_status = PAYMENT_MAP.get(order_data.get('payment_status', 'PENDING'), 'UNPAID')
                    
                    # Create order
                    order = Order.objects.create(
                        order_id=uuid.uuid4(),
                        customer_id=customer_id,
                        customer_name=customer['name'],
                        customer_email=customer['email'],
                        order_status=order_status,
                        payment_status=payment_status,
                        shipping=Decimal('10.00'),
                    )
                    
                    # Create order items
                    order_id_str = str(order_data['order_id'])
                    if order_id_str in items_by_order:
                        for item_data in items_by_order[order_id_str]:
                            product_id = int(item_data['product_id'])
                            product = MockCatalogService.get_product(product_id)
                            
                            if not product:
                                self.stdout.write(self.style.WARNING(
                                    f'  ⚠ Skipping item: Product {product_id} not found'
                                ))
                                continue
                            
                            order_item = OrderItem.objects.create(
                                order=order,
                                product_id=product_id,
                                sku=item_data['sku'],
                                product_name=product['name'],
                                quantity=int(item_data['quantity']),
                                unit_price=Decimal(item_data['unit_price']),
                            )
                            order_item.calculate_line_total()
                            order_item.save()
                    
                    # Calculate order totals
                    order.calculate_totals()
                    order.save()
                    
                    imported += 1
                    if imported % 50 == 0:
                        self.stdout.write(f'  ✓ Imported {imported} orders...')
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'  ✗ Error importing order {order_data.get("order_id", "unknown")}: {e}'
                    ))
                    skipped += 1
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write('='*70)
        self.stdout.write(f'✓ Imported: {imported} orders')
        self.stdout.write(f'⚠ Skipped: {skipped} orders')
        self.stdout.write(f'✓ Total Items: {OrderItem.objects.count()}')
        self.stdout.write('='*70)