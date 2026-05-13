from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('history/', views.history_view, name='history'),
    path('delete-trip/<int:trip_id>/', views.delete_trip, name='delete_trip'),
    # Ye naya route hai AI se chat karne ke liye
    path('refine_itinerary/', views.refine_itinerary, name='refine_itinerary'),
] 