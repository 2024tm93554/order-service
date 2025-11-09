from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('api/orders/stats/', views.mock_orders_stats, name='mock_orders_stats'),  
    path('api/payments/stats/', views.mock_payments_stats, name='mock_payments_stats'),  
    path('api/inventory/stats/', views.mock_inventory_stats, name='mock_inventory_stats'),  
    path('api/customers/stats/', views.mock_customers_stats, name='mock_customers_stats'),  
    path('api/products/stats/', views.mock_products_stats, name='mock_products_stats'),  
    path('api/recent-activity/', views.recent_activity, name='recent_activity'),
]