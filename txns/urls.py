from django.urls import path

from .views import CompareRealtimeData


urlpatterns = [
    path('compare-data/', CompareRealtimeData.as_view(), name='compare-realtime-data'),
]
