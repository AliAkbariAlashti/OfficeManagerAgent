from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import process_request, create_meeting, get_meetings_by_date_range, find_free_slots
from datetime import datetime

@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        user_input = request.POST.get('message', '')
        response = process_request(user_input)
        
        if "جلسه جدید" in user_input:
            parts = user_input.split('،')
            title = parts[0].replace("جلسه جدید", "").strip()
            date = datetime.now().date()
            time = parts[2].strip() if len(parts) > 2 else "10:00"
            location = parts[3].strip() if len(parts) > 3 else ""
            response = create_meeting(title, date, time, location)
        elif "جلسات امروز" in user_input:
            today = datetime.now().date()
            response = get_meetings_by_date_range(today, today)
        elif "زمان آزاد" in user_input:
            date = datetime.now().date()
            free_slots = find_free_slots(date)
            response = f"Free slots: {', '.join(free_slots)}"
        
        return JsonResponse({'response': response})
    return render(request, 'assistant/chat.html')
