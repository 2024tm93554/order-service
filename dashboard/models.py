from django.db import models
from orders.models import Order  # Import Order from the orders app instead

# Remove the duplicate Order model definition
# If you need other dashboard-specific models, define them here