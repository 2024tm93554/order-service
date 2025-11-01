from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    
    def ready(self):
        """Load CSV data when Django starts"""
        from orders.services import (MockCustomerService, MockCatalogService, 
                                     MockInventoryService)
        
        # Load all ECI CSV data into memory
        try:
            MockCustomerService.load_from_csv('eci_customers.csv')
            MockCatalogService.load_from_csv('eci_products.csv')
            MockInventoryService.load_from_csv('eci_inventory.csv')
            print("\n✓ ECI CSV data loaded successfully!")
        except Exception as e:
            print(f"\n⚠ Warning: Could not load ECI CSV data: {e}")