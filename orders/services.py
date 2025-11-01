import csv
import uuid
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CSV Data Loader (unchanged)
# ============================================================================

class CSVDataLoader:
    """Utility to load data from CSV files"""
    
    @staticmethod
    def get_csv_path(filename):
        """Get path to CSV file in seed_data folder"""
        return Path(settings.BASE_DIR) / 'seed_data' / filename
    
    @staticmethod
    def load_csv_to_dict(filename, key_field='id'):
        """Load CSV file into dictionary keyed by specified field"""
        csv_path = CSVDataLoader.get_csv_path(filename)
        data = {}
        
        if not csv_path.exists():
            print(f"Warning: {filename} not found at {csv_path}")
            return data
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = int(row[key_field]) if row[key_field].isdigit() else row[key_field]
                    data[key] = row
            print(f"✓ Loaded {len(data)} records from {filename}")
        except Exception as e:
            print(f"✗ Error loading {filename}: {e}")
        
        return data
    
    @staticmethod
    def load_csv_to_list(filename):
        """Load CSV file into list of dictionaries"""
        csv_path = CSVDataLoader.get_csv_path(filename)
        data = []
        
        if not csv_path.exists():
            print(f"Warning: {filename} not found at {csv_path}")
            return data
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            print(f"✓ Loaded {len(data)} records from {filename}")
        except Exception as e:
            print(f"✗ Error loading {filename}: {e}")
        
        return data


# ============================================================================
# Mock Services (unchanged - your existing mock services)
# ============================================================================

class MockCustomerService:
    """Mock Customer Service with CSV data from eci_customers"""
    
    CUSTOMERS = {}
    
    @classmethod
    def load_from_csv(cls, filename='eci_customers.csv'):
        """Load customers from CSV"""
        cls.CUSTOMERS = CSVDataLoader.load_csv_to_dict(filename, key_field='customer_id')
        
        for customer_id, customer in cls.CUSTOMERS.items():
            cls.CUSTOMERS[customer_id] = {
                'customer_id': int(customer['customer_id']),
                'name': customer['name'],
                'email': customer['email'],
                'phone': customer.get('phone', ''),
                'created_at': customer.get('created_at', '')
            }
    
    @classmethod
    def get_customer(cls, customer_id):
        """Get customer by ID"""
        if not cls.CUSTOMERS:
            cls.load_from_csv()
        return cls.CUSTOMERS.get(customer_id)


class MockCatalogService:
    """Mock Catalog Service with CSV data from eci_products"""
    
    PRODUCTS = {}
    
    @classmethod
    def load_from_csv(cls, filename='eci_products.csv'):
        """Load products from CSV"""
        cls.PRODUCTS = CSVDataLoader.load_csv_to_dict(filename, key_field='product_id')
        
        for product_id, product in cls.PRODUCTS.items():
            is_active_str = str(product.get('is_active', 'True')).lower()
            is_active = is_active_str in ['true', '1', 'yes']
            
            cls.PRODUCTS[product_id] = {
                'product_id': int(product['product_id']),
                'sku': product['sku'],
                'name': product['name'],
                'category': product.get('category', ''),
                'price': Decimal(str(product['price'])),
                'is_active': is_active
            }
    
    @classmethod
    def get_product(cls, product_id):
        """Get product by ID"""
        if not cls.PRODUCTS:
            cls.load_from_csv()
        return cls.PRODUCTS.get(product_id)
    
    @classmethod
    def get_product_by_sku(cls, sku):
        """Get product by SKU"""
        if not cls.PRODUCTS:
            cls.load_from_csv()
        for product in cls.PRODUCTS.values():
            if product['sku'] == sku:
                return product
        return None


class MockInventoryService:
    """Mock Inventory Service with CSV data from eci_inventory"""
    
    INVENTORY = {}
    
    @classmethod
    def load_from_csv(cls, filename='eci_inventory.csv'):
        """Load inventory from CSV"""
        inventory_list = CSVDataLoader.load_csv_to_list(filename)
        
        for item in inventory_list:
            product_id = int(item['product_id'])
            warehouse = item['warehouse']
            key = f"{product_id}-{warehouse}"
            
            cls.INVENTORY[key] = {
                'inventory_id': int(item['inventory_id']),
                'product_id': product_id,
                'warehouse': warehouse,
                'on_hand': int(item['on_hand']),
                'reserved': int(item.get('reserved', 0)),
                'updated_at': item.get('updated_at', '')
            }
    
    @classmethod
    def get_inventory(cls, product_id, warehouse=None):
        """Get inventory for product"""
        if not cls.INVENTORY:
            cls.load_from_csv()
        
        if warehouse:
            key = f"{product_id}-{warehouse}"
            return cls.INVENTORY.get(key)
        
        result = []
        for key, inv in cls.INVENTORY.items():
            if inv['product_id'] == product_id:
                result.append(inv)
        return result
    
    @classmethod
    def check_availability(cls, product_id, quantity, warehouse=None):
        """Check if product is available"""
        if not cls.INVENTORY:
            cls.load_from_csv()
        
        if warehouse:
            inv = cls.get_inventory(product_id, warehouse)
            if inv:
                available = inv['on_hand'] - inv['reserved']
                return available >= quantity, warehouse
        else:
            inventories = cls.get_inventory(product_id)
            for inv in inventories:
                available = inv['on_hand'] - inv['reserved']
                if available >= quantity:
                    return True, inv['warehouse']
        
        return False, None
    
    @classmethod
    def reserve_stock(cls, product_id, sku, quantity):
        """Mock reservation - checks actual inventory from CSV"""
        if not cls.INVENTORY:
            cls.load_from_csv()
        
        available, warehouse = cls.check_availability(product_id, quantity)
        
        if available:
            return {
                'success': True,
                'reservation_id': f'RES-{uuid.uuid4().hex[:12]}',
                'warehouse': warehouse,
                'quantity': quantity
            }
        else:
            return {
                'success': False,
                'error': f'Insufficient stock for product {product_id}'
            }
    
    @classmethod
    def release_reservation(cls, reservation_id):
        """Mock release - always succeeds"""
        return {'success': True, 'released': reservation_id}


class MockPaymentService:
    """Mock Payment Service - simple simulation"""
    
    @staticmethod
    def charge(order_id, amount, idempotency_key):
        """Mock charge - always succeeds"""
        return {
            'success': True,
            'payment_id': f'PAY-{uuid.uuid4().hex[:12]}',
            'amount': amount,
            'status': 'PAID'
        }
    
    @staticmethod
    def refund(payment_id, amount):
        """Mock refund - always succeeds"""
        return {
            'success': True,
            'refund_id': f'REF-{uuid.uuid4().hex[:12]}',
            'amount': amount,
            'status': 'REFUNDED'
        }


# ============================================================================
# Service Selection with Fallback
# ============================================================================

def get_customer_service():
    """Get Customer Service with fallback"""
    try:
        from .service_clients import RealCustomerService
        from .service_wrapper import CustomerServiceWrapper, get_service_with_fallback
        
        return get_service_with_fallback(
            RealCustomerService,
            MockCustomerService,
            CustomerServiceWrapper
        )
    except ImportError:
        logger.warning("Real services not available, using mock CustomerService")
        return MockCustomerService


def get_catalog_service():
    """Get Catalog Service with fallback"""
    try:
        from .service_clients import RealCatalogService
        from .service_wrapper import CatalogServiceWrapper, get_service_with_fallback
        
        return get_service_with_fallback(
            RealCatalogService,
            MockCatalogService,
            CatalogServiceWrapper
        )
    except ImportError:
        logger.warning("Real services not available, using mock CatalogService")
        return MockCatalogService


def get_inventory_service():
    """Get Inventory Service with fallback"""
    try:
        from .service_clients import RealInventoryService
        from .service_wrapper import InventoryServiceWrapper, get_service_with_fallback
        
        return get_service_with_fallback(
            RealInventoryService,
            MockInventoryService,
            InventoryServiceWrapper
        )
    except ImportError:
        logger.warning("Real services not available, using mock InventoryService")
        return MockInventoryService


def get_payment_service():
    """Get Payment Service with fallback"""
    try:
        from .service_clients import RealPaymentService
        from .service_wrapper import PaymentServiceWrapper, get_service_with_fallback
        
        return get_service_with_fallback(
            RealPaymentService,
            MockPaymentService,
            PaymentServiceWrapper
        )
    except ImportError:
        logger.warning("Real services not available, using mock PaymentService")
        return MockPaymentService


# ============================================================================
# Order Service - Main Business Logic
# ============================================================================

class OrderService:
    """Business logic for order operations with automatic service fallback"""
    
    # Initialize services with fallback support
    CustomerService = get_customer_service()
    CatalogService = get_catalog_service()
    InventoryService = get_inventory_service()
    PaymentService = get_payment_service()
    
    @staticmethod
    @transaction.atomic
    def create_order(customer_id, items_data, idempotency_key=None, shipping=Decimal('10.00')):
        """Create a new order with full workflow"""
        from .models import Order, OrderItem
        
        # Check idempotency
        if idempotency_key:
            existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing_order:
                logger.info(f"Idempotent request: returning existing order {existing_order.order_id}")
                return existing_order, False
        
        # Get customer info
        customer_info = OrderService.CustomerService.get_customer(customer_id)
        if not customer_info:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Create pending order
        order = Order.objects.create(
            customer_id=customer_id,
            customer_name=customer_info['name'],
            customer_email=customer_info['email'],
            idempotency_key=idempotency_key,
            shipping=shipping,
            order_status='PENDING',
            payment_status='UNPAID'
        )
        
        logger.info(f"Created order {order.order_id} for customer {customer_id}")
        
        # Create order items and reserve inventory
        reservations = []
        try:
            for item_data in items_data:
                # Get product info from catalog service
                product = OrderService.CatalogService.get_product(item_data['product_id'])
                if not product:
                    raise ValueError(f"Product {item_data['product_id']} not found")
                
                # Check if product is active
                if not product.get('is_active', True):
                    raise ValueError(f"Product {product['name']} is not active")
                
                # Reserve inventory
                reservation = OrderService.InventoryService.reserve_stock(
                    product['product_id'],
                    product['sku'],
                    item_data['quantity']
                )
                
                if not reservation['success']:
                    raise ValueError(
                        f"Cannot reserve {product['name']}: "
                        f"{reservation.get('error', 'Insufficient stock')}"
                    )
                
                reservations.append(reservation['reservation_id'])
                logger.info(
                    f"Reserved {item_data['quantity']} units of {product['name']} "
                    f"(reservation: {reservation['reservation_id']})"
                )
                
                # Create order item
                order_item = OrderItem.objects.create(
                    order=order,
                    product_id=product['product_id'],
                    sku=product['sku'],
                    product_name=product['name'],
                    quantity=item_data['quantity'],
                    unit_price=product['price'],
                    reservation_id=reservation['reservation_id'],
                    warehouse=reservation['warehouse']
                )
                order_item.calculate_line_total()
                order_item.save()
            
            # Calculate totals
            order.calculate_totals()
            order.save()
            
            # Process payment
            payment_result = OrderService.PaymentService.charge(
                order.order_id,
                order.order_total,
                idempotency_key or str(uuid.uuid4())
            )
            
            if payment_result['success']:
                order.order_status = 'CONFIRMED'
                order.payment_status = 'PAID'
                order.save()
                logger.info(f"Order {order.order_id} confirmed and paid")
            else:
                raise ValueError(f"Payment failed: {payment_result.get('error', 'Unknown error')}")
            
            return order, True
            
        except Exception as e:
            logger.error(f"Order creation failed: {str(e)}")
            
            # Cleanup: Release all reservations
            for res_id in reservations:
                try:
                    OrderService.InventoryService.release_reservation(res_id)
                    logger.info(f"Released reservation {res_id}")
                except Exception as release_error:
                    logger.error(f"Failed to release reservation {res_id}: {str(release_error)}")
            
            # Delete the order
            order.delete()
            logger.info(f"Rolled back order creation")
            
            # Re-raise the exception
            raise
    
    @staticmethod
    @transaction.atomic
    def cancel_order(order):
        """Cancel an order"""
        if order.order_status == 'CANCELLED':
            logger.info(f"Order {order.order_id} already cancelled")
            return order
        
        if order.order_status == 'DELIVERED':
            raise ValueError("Cannot cancel delivered order")
        
        # Release all reservations
        for item in order.items.all():
            if item.reservation_id:
                try:
                    OrderService.InventoryService.release_reservation(item.reservation_id)
                    logger.info(f"Released reservation {item.reservation_id}")
                except Exception as e:
                    logger.error(f"Failed to release reservation {item.reservation_id}: {str(e)}")
        
        # Refund if paid
        if order.payment_status == 'PAID':
            try:
                OrderService.PaymentService.refund(
                    f'PAY-{order.order_id}',
                    order.order_total
                )
                order.payment_status = 'REFUNDED'
                logger.info(f"Refunded payment for order {order.order_id}")
            except Exception as e:
                logger.error(f"Failed to refund order {order.order_id}: {str(e)}")
                # Continue with cancellation even if refund fails
        
        order.order_status = 'CANCELLED'
        order.save()
        logger.info(f"Order {order.order_id} cancelled")
        
        return order