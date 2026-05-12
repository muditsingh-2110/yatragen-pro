from django.db import models
from django.contrib.auth.models import User

class TripPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.CharField(max_length=255)
    days = models.IntegerField()
    style = models.CharField(max_length=50)
    itinerary_html = models.TextField() # AI ka pura response yahan save hoga
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.destination}"