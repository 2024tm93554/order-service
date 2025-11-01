from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Order, OrderItem
from .serializers import (OrderSerializer, OrderCreateSerializer, 
                          OrderItemSerializer)
from .services import OrderService

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order operations
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['order_status', 'payment_status', 'customer_id']
    ordering_fields = ['created_at', 'order_total']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def create(self, request):
        """Create a new order with idempotency support"""
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get idempotency key from header
        idempotency_key = request.headers.get('Idempotency-Key')
        
        try:
            order, created = OrderService.create_order(
                customer_id=serializer.validated_data['customer_id'],
                items_data=serializer.validated_data['items'],
                idempotency_key=idempotency_key,
                shipping=serializer.validated_data.get('shipping')
            )
            
            response_serializer = OrderSerializer(order)
            http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            
            return Response(response_serializer.data, status=http_status)
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        try:
            cancelled_order = OrderService.cancel_order(order)
            serializer = OrderSerializer(cancelled_order)
            return Response(serializer.data)
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Manually confirm an order"""
        order = self.get_object()
        
        if order.order_status != 'PENDING':
            return Response(
                {'error': 'Only pending orders can be confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.order_status = 'CONFIRMED'
        order.save()
        
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """Get items for a specific order"""
        order = self.get_object()
        items = order.items.all()
        serializer = OrderItemSerializer(items, many=True)
        return Response(serializer.data)