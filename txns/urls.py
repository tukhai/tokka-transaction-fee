from django.urls import path

from .views import CompareRealtimeData, Transaction


urlpatterns = [
    path('compare_data/', CompareRealtimeData.as_view(), name='compare_realtime_data'),
    path('get_transaction_by_hash/', Transaction.as_view(), name='get_transaction_by_hash'),
]
