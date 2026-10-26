from django.urls import path
from routing_api.views import AnalyzeRoutesAPIView

urlpatterns = [
    path('api/v1/routes/analyze/', AnalyzeRoutesAPIView.as_view(), name='analyze-routes'),
]
