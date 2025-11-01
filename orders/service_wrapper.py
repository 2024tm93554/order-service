"""
Service wrapper with automatic fallback to mock services
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ServiceWrapper:
    """
    Wrapper that attempts to use real services and falls back to mock services
    if real services fail or are disabled
    """
    
    def __init__(self, real_service_class, mock_service_class, service_name):
        self.real_service = real_service_class
        self.mock_service = mock_service_class
        self.service_name = service_name
        self.use_real_services = getattr(settings, 'USE_REAL_SERVICES', False)
        self.enable_fallback = getattr(settings, 'ENABLE_SERVICE_FALLBACK', True)
    
    def _call_with_fallback(self, method_name, *args, **kwargs):
        """
        Call service method with automatic fallback to mock
        """
        # If real services disabled, use mock directly
        if not self.use_real_services:
            logger.debug(f"{self.service_name}: Using mock service (real services disabled)")
            method = getattr(self.mock_service, method_name)
            return method(*args, **kwargs)
        
        # Try real service first
        try:
            logger.debug(f"{self.service_name}.{method_name}: Attempting real service")
            method = getattr(self.real_service, method_name)
            result = method(*args, **kwargs)
            logger.info(f"{self.service_name}.{method_name}: Real service succeeded")
            return result
        
        except Exception as e:
            logger.warning(
                f"{self.service_name}.{method_name}: Real service failed - {str(e)}"
            )
            
            # If fallback is disabled, re-raise the exception
            if not self.enable_fallback:
                logger.error(f"{self.service_name}: Fallback disabled, raising exception")
                raise
            
            # Fall back to mock service
            try:
                logger.info(f"{self.service_name}.{method_name}: Falling back to mock service")
                method = getattr(self.mock_service, method_name)
                result = method(*args, **kwargs)
                logger.info(f"{self.service_name}.{method_name}: Mock service succeeded")
                return result
            
            except Exception as mock_error:
                logger.error(
                    f"{self.service_name}.{method_name}: Both real and mock services failed. "
                    f"Real: {str(e)}, Mock: {str(mock_error)}"
                )
                raise Exception(
                    f"{self.service_name} unavailable: Real service failed ({str(e)}), "
                    f"Mock fallback also failed ({str(mock_error)})"
                )


class CustomerServiceWrapper(ServiceWrapper):
    """Customer Service with fallback"""
    
    def __init__(self, real_service, mock_service):
        super().__init__(real_service, mock_service, "CustomerService")
    
    def get_customer(self, customer_id):
        return self._call_with_fallback('get_customer', customer_id)


class CatalogServiceWrapper(ServiceWrapper):
    """Catalog Service with fallback"""
    
    def __init__(self, real_service, mock_service):
        super().__init__(real_service, mock_service, "CatalogService")
    
    def get_product(self, product_id):
        return self._call_with_fallback('get_product', product_id)
    
    def get_product_by_sku(self, sku):
        return self._call_with_fallback('get_product_by_sku', sku)


class InventoryServiceWrapper(ServiceWrapper):
    """Inventory Service with fallback"""
    
    def __init__(self, real_service, mock_service):
        super().__init__(real_service, mock_service, "InventoryService")
    
    def get_inventory(self, product_id, warehouse=None):
        return self._call_with_fallback('get_inventory', product_id, warehouse)
    
    def check_availability(self, product_id, quantity, warehouse=None):
        return self._call_with_fallback('check_availability', product_id, quantity, warehouse)
    
    def reserve_stock(self, product_id, sku, quantity):
        return self._call_with_fallback('reserve_stock', product_id, sku, quantity)
    
    def release_reservation(self, reservation_id):
        return self._call_with_fallback('release_reservation', reservation_id)


class PaymentServiceWrapper(ServiceWrapper):
    """Payment Service with fallback"""
    
    def __init__(self, real_service, mock_service):
        super().__init__(real_service, mock_service, "PaymentService")
    
    def charge(self, order_id, amount, idempotency_key):
        return self._call_with_fallback('charge', order_id, amount, idempotency_key)
    
    def refund(self, payment_id, amount):
        return self._call_with_fallback('refund', payment_id, amount)


# Factory function to create service instances with fallback
def get_service_with_fallback(real_service_class, mock_service_class, wrapper_class):
    """
    Factory to create service wrapper with proper fallback
    """
    return wrapper_class(real_service_class, mock_service_class)