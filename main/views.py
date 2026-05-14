from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import TripPlan
import markdown, requests, re
from groq import Groq
import os
# Ab hardcoded key nahi, environment variable use karenge
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))
def get_weather(city):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url).json()
        if 'results' in geo_res:
            lat, lon = geo_res['results'][0]['latitude'], geo_res['results'][0]['longitude']
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            w_res = requests.get(w_url).json()
            return f"{w_res['current_weather']['temperature']}°C"
    except: return "N/A"
    return "N/A"

def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid(): login(request, form.save()); return redirect('home')
    else: form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid(): login(request, form.get_user()); return redirect('home')
    else: form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request); return redirect('home')

# Helper function to clean AI's messy markdown formatting
def clean_ai_response(raw_text):
    # Remove markdown code block wrappers if AI hallucinates them
    text = re.sub(r'^```(?:markdown|html)?\n', '', raw_text, flags=re.MULTILINE)
    text = re.sub(r'\n```$', '', text, flags=re.MULTILINE)
    # FORCE a blank line before the table so the markdown parser ALWAYS renders it
    text = text.replace('| Category |', '\n\n| Category |')
    return text.strip()

def home(request):
    itinerary, weather = "", ""
    if request.method == "POST":
        source = request.POST.get('source')           # Ye line add kar
        start_date = request.POST.get('start_date')
        dest = request.POST.get('destination')
        days = request.POST.get('days')
        style = request.POST.get('style')
        pers = request.POST.get('persons')
        weather = get_weather(dest)
        
        multi_agent_prompt = f"""
        Act as an Expert Travel Editor. Create a {days}-day itinerary from {source} to {dest} starting on {start_date} for {pers} people on a {style} budget.        
        STRICT FORMATTING RULES - IF YOU FAIL THESE, THE SYSTEM CRASHES:
        1. HEADINGS: Use EXACTLY **Day 1: [Name]**. No other bolding.
        2. POINTS: Use bullet points (-). Always include commute mode/cost.
        3. SECTIONS: You MUST include '**Recommended Stays:**' (4 options with price/fake phone) and '**Special Recommendations:**'.
        4. TABLE: You MUST end with this EXACT table format. 
        
        | Category | Estimated Cost |
        |---|---|
        | Stay | ₹... |
        | Food | ₹... |
        | Transport | ₹... |
        | Total | ₹... |
        
        DO NOT wrap the response in ```markdown. Output plain text only. No intro/outro.
        """
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": multi_agent_prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            
            clean_response = clean_ai_response(completion.choices[0].message.content)
            itinerary = markdown.markdown(clean_response, extensions=['tables'])
            itinerary = itinerary.replace('<table>', '<table class="table table-bordered table-striped mt-3">')
            
            if request.user.is_authenticated:
                TripPlan.objects.create(user=request.user, destination=dest, days=days, style=style, itinerary_html=itinerary)
                
        except Exception as e:
            itinerary = f"<div class='alert alert-danger'>API Error: {str(e)}</div>"
            
    return render(request, 'index.html', {'itinerary': itinerary, 'weather': weather})

def refine_itinerary(request):
    if request.method == "POST":
        current_plan = request.POST.get('current_plan')
        user_request = request.POST.get('user_request')
        
        refine_prompt = f"""
        Act as an Expert Travel Editor.
        Current Plan: {current_plan}
        Change requested: "{user_request}"
        
        Rewrite the ENTIRE itinerary incorporating this change perfectly.
        
        STRICT FORMATTING RULES - IF YOU FAIL THESE, THE SYSTEM CRASHES:
        1. HEADINGS: Use EXACTLY **Day 1: [Name]**. No other bolding.
        2. POINTS: Use bullet points (-). Always include commute mode/cost.
        3. SECTIONS: You MUST include '**Recommended Stays:**' and '**Special Recommendations:**'.
        4. TABLE: You MUST end with this EXACT table format. Do not change the headers.
        
        | Category | Estimated Cost |
        |---|---|
        | Stay | ₹... |
        | Food | ₹... |
        | Transport | ₹... |
        | Total | ₹... |
        
        DO NOT wrap the response in 
```markdown. Output plain text only. No intro/outro.
        """
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": refine_prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            
            clean_response = clean_ai_response(completion.choices[0].message.content)
            updated_html = markdown.markdown(clean_response, extensions=['tables'])
            updated_html = updated_html.replace('<table>', '<table class="table table-bordered table-striped mt-3">')
            
            return JsonResponse({'success': True, 'updated_html': updated_html})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid Request'})

@login_required
def history_view(request):
    trips = TripPlan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'history.html', {'trips': trips})

@login_required
def delete_trip(request, trip_id):
    trip = get_object_or_404(TripPlan, id=trip_id, user=request.user)
    if request.method == "POST": trip.delete()
    return redirect('history')