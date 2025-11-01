import requests
import uuid
from decimal import Decimal
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base class for service clients with common functionality"""
    
    @staticmethod
    def make_request(url, method='GET', data=None, timeout=10):
        """Make HTTP request with error handling"""
        try:
            if method == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Service request failed: {url} - {str(e)}")
            raise ServiceUnavailableError(f"Service call failed: {str(e)}")


class ServiceUnavailableError(Exception):
    """Raised when external service is unavailable"""
    pass


class RealCustomerService:
    """Real Customer Service Client"""
    
    @classmethod
    def get_customer(cls, customer_id):
        """Get customer by ID from Customer Service"""
        url = f"{settings.CUSTOMER_SERVICE_URL}/{customer_id}"
        
        try:
            response = ServiceClient.make_request(url)
            
            return {
                'customer_id': response['customer_id'],
                'name': response['name'],
                'email': response['email'],
                'phone': response.get('phone', ''),
                'created_at': response.get('created_at', '')
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Failed to fetch customer {customer_id}: {str(e)}")
            raise ServiceUnavailableError(f"Customer service unavailable: {str(e)}")


class RealCatalogService:
    """Real Catalog Service Client"""
    
    @classmethod
    def get_product(cls, product_id):
        """Get product by ID from Catalog Service"""
        url = f"{settings.CATALOG_SERVICE_URL}/{product_id}"
        
        try:
            response = ServiceClient.make_request(url)
            
            return {
                'product_id': response['product_id'],
                'sku': response['sku'],
                'name': response['name'],
                'category': response.get('category', ''),
                'price': Decimal(str(response['price'])),
                'is_active': response.get('is_active', True)
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Failed to fetch product {product_id}: {str(e)}")
            raise ServiceUnavailableError(f"Catalog service unavailable: {str(e)}")
    
    @classmethod
    def get_product_by_sku(cls, sku):
        """Get product by SKU from Catalog Service"""
        url = f"{settings.CATALOG_SERVICE_URL}?sku={sku}"
        
        try:
            response = ServiceClient.make_request(url)
            
            if isinstance(response, list) and len(response) > 0:
                product = response[0]
            else:
                product = response
            
            return {
                'product_id': product['product_id'],
                'sku': product['sku'],
                'name': product['name'],
                'category': product.get('category', ''),
                'price': Decimal(str(product['price'])),
                'is_active': product.get('is_active', True)
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Failed to fetch product by SKU {sku}: {str(e)}")
            raise ServiceUnavailableError(f"Catalog service unavailable: {str(e)}")


class RealInventoryService:
    """Real Inventory Service Client"""
    
    @classmethod
    def get_inventory(cls, product_id, warehouse=None):
        """Get inventory for product from Inventory Service"""
        if warehouse:
            url = f"{settings.INVENTORY_SERVICE_URL}/{product_id}?warehouse={warehouse}"
        else:
            url = f"{settings.INVENTORY_SERVICE_URL}/{product_id}"
        
        try:
            response = ServiceClient.make_request(url)
            
            if isinstance(response, list):
                return [cls._format_inventory(inv) for inv in response]
            else:
                return cls._format_inventory(response)
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Failed to fetch inventory for product {product_id}: {str(e)}")
            raise ServiceUnavailableError(f"Inventory service unavailable: {str(e)}")
    
    @staticmethod
    def _format_inventory(inv):
        """Format inventory response"""
        return {
            'inventory_id': inv['inventory_id'],
            'product_id': inv['product_id'],
            'warehouse': inv['warehouse'],
            'on_hand': int(inv['on_hand']),
            'reserved': int(inv.get('reserved', 0)),
            'updated_at': inv.get('updated_at', '')
        }
    
    @classmethod
    def check_availability(cls, product_id, quantity, warehouse=None):
        """Check if product is available"""
        try:
            inventory = cls.get_inventory(product_id, warehouse)
            
            if not inventory:
                return False, None
            
            if warehouse:
                available = inventory['on_hand'] - inventory['reserved']
                return available >= quantity, warehouse
            else:
                for inv in inventory:
                    available = inv['on_hand'] - inv['reserved']
                    if available >= quantity:
                        return True, inv['warehouse']
            
            return False, None
        except ServiceUnavailableError as e:
            logger.error(f"Availability check failed: {str(e)}")
            raise
    
    @classmethod
    def reserve_stock(cls, product_id, sku, quantity):
        """Reserve stock via Inventory Service"""
        url = f"{settings.INVENTORY_SERVICE_URL}/reserve"
        
        data = {
            'product_id': product_id,
            'sku': sku,
            'quantity': quantity
        }
        
        try:
            response = ServiceClient.make_request(url, method='POST', data=data)
            
            return {
                'success': response.get('success', True),
                'reservation_id': response['reservation_id'],
                'warehouse': response['warehouse'],
                'quantity': response['quantity'],
                'error': response.get('error')
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Failed to reserve stock for product {product_id}: {str(e)}")
            raise ServiceUnavailableError(f"Inventory service unavailable: {str(e)}")
    
    @classmethod
    def release_reservation(cls, reservation_id):
        """Release stock reservation"""
        url = f"{settings.INVENTORY_SERVICE_URL}/reserve/{reservation_id}"
        
        try:
            response = ServiceClient.make_request(url, method='DELETE')
            return {
                'success': response.get('success', True),
                'released': reservation_id
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Failed to release reservation {reservation_id}: {str(e)}")
            raise ServiceUnavailableError(f"Inventory service unavailable: {str(e)}")


class RealPaymentService:
    """Real Payment Service Client"""
    
    @staticmethod
    def charge(order_id, amount, idempotency_key):
        """Process payment charge"""
        url = f"{settings.PAYMENT_SERVICE_URL}/charge"
        
        data = {
            'order_id': str(order_id),
            'amount': str(amount),
            'idempotency_key': idempotency_key
        }
        
        try:
            response = ServiceClient.make_request(url, method='POST', data=data)
            
            return {
                'success': response.get('success', True),
                'payment_id': response['payment_id'],
                'amount': Decimal(str(response['amount'])),
                'status': response['status'],
                'error': response.get('error')
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Payment failed for order {order_id}: {str(e)}")
            raise ServiceUnavailableError(f"Payment service unavailable: {str(e)}")
    
    @staticmethod
    def refund(payment_id, amount):
        """Process payment refund"""
        url = f"{settings.PAYMENT_SERVICE_URL}/refund"
        
        data = {
            'payment_id': payment_id,
            'amount': str(amount)
        }
        
        try:
            response = ServiceClient.make_request(url, method='POST', data=data)
            
            return {
                'success': response.get('success', True),
                'refund_id': response['refund_id'],
                'amount': Decimal(str(response['amount'])),
                'status': response['status'],
                'error': response.get('error')
            }
        except (ServiceUnavailableError, Exception) as e:
            logger.error(f"Refund failed for payment {payment_id}: {str(e)}")
            raise ServiceUnavailableError(f"Payment service unavailable: {str(e)}")