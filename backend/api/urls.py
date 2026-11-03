from django.urls import path
from .views import HomeView, HealthView, SearchView, ChatView, StatsView, EventsView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/search/", SearchView.as_view(), name="search"),
    path("api/chat/", ChatView.as_view(), name="chat"),
    path("api/stats/", StatsView.as_view(), name="stats"),
    path("api/events/", EventsView.as_view(), name="events"),
]
