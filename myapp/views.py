from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
import bcrypt
import json

db = settings.MONGO_DB
users_collection      = db['users']
units_collection      = db['course_units']
agreements_collection = db['agreements']

def index(request):
    return render(request, 'myapp/index.html')

def apply(request):
    return render(request, 'myapp/apply.html')

def login(request):
    return render(request, 'myapp/login.html')

def login_student(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = users_collection.find_one({'username': username, 'role': 'student'})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            request.session['username'] = username
            request.session['role'] = 'student'
            return redirect('student_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'myapp/login_student.html')

def login_agent(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = users_collection.find_one({'username': username, 'role': 'agent'})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            request.session['username'] = username
            request.session['role'] = 'agent'
            agreement = agreements_collection.find_one({'username': username, 'accepted': True})
            if not agreement:
                return redirect('agent_agreement')
            return redirect('agent_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'myapp/login_agent.html')

def login_professor(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = users_collection.find_one({'username': username, 'role': 'professor'})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            request.session['username'] = username
            request.session['role'] = 'professor'
            return redirect('professor_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'myapp/login_professor.html')

def signup(request):
    if request.method == 'POST':
        pass
    return render(request, 'myapp/signup.html')

def logout(request):
    request.session.flush()
    return redirect('login_select')

def agent_agreement(request):
    if request.session.get('role') != 'agent':
        return redirect('login_select')
    if request.method == 'POST':
        username = request.session.get('username')
        agreements_collection.update_one(
            {'username': username},
            {'$set': {'username': username, 'accepted': True}},
            upsert=True
        )
        return redirect('agent_dashboard')
    return render(request, 'myapp/agent_agreement.html')

def student_dashboard(request):
    if request.session.get('role') != 'student':
        return redirect('login_select')
    username = request.session.get('username')
    units = list(units_collection.find({}, {'_id': 0}))
    return render(request, 'myapp/dashboard_student.html', {
        'username': username,
        'units': units,
    })

def professor_dashboard(request):
    if request.session.get('role') != 'professor':
        return redirect('login_select')
    username = request.session.get('username')
    units = list(units_collection.find({}))
    for unit in units:
        unit['id'] = str(unit['_id'])  # add this line
        unit['_id'] = str(unit['_id'])
    student_count = users_collection.count_documents({'role': 'student'})
    return render(request, 'myapp/dashboard_professor.html', {
        'username': username,
        'units': units,
        'student_count': student_count,
    })

def agent_dashboard(request):
    if request.session.get('role') != 'agent':
        return redirect('login_select')
    username = request.session.get('username')
    agreement = agreements_collection.find_one({'username': username, 'accepted': True})
    if not agreement:
        return redirect('agent_agreement')
    students = list(users_collection.find({'role': 'student'}, {'password': 0}))
    for s in students:
        s['_id'] = str(s['_id'])
    active_count  = sum(1 for s in students if s.get('status', 'active') == 'active')
    pending_count = sum(1 for s in students if s.get('status') == 'pending')
    return render(request, 'myapp/dashboard_agent.html', {
        'username': username,
        'students': students,
        'active_count': active_count,
        'pending_count': pending_count,
    })

def update_unit(request):
    if request.session.get('role') != 'professor':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method == 'POST':
        try:
            from bson import ObjectId
            data    = json.loads(request.body)
            unit_id = data.get('unit_id')
            index   = data.get('index', 0)
            title   = data.get('title', '')
            desc    = data.get('description', '')
            icon    = data.get('icon', '')
            if unit_id:
                units_collection.update_one(
                    {'_id': ObjectId(unit_id)},
                    {'$set': {'title': title, 'description': desc, 'icon': icon}}
                )
            else:
                units_collection.insert_one({
                    'title': title, 'description': desc,
                    'icon': icon, 'locked': False, 'url': '#', 'order': index
                })
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})
def chap1(request):
    if request.session.get('role') != 'student':
        return redirect('login_select')
    coursework_unlocked = request.session.get('chap1_coursework_unlocked', False)
    return render(request, 'myapp/chap1.html', {
        'username': request.session.get('username'),
        'coursework_unlocked': coursework_unlocked,
    })


def ass1(request):
    if request.session.get('role') != 'student':
        return redirect('login_select')
    return render(request, 'myapp/ass1.html')


def result1(request):
    if request.method == 'POST':
        score = int(request.POST.get('score', 0))
        total = int(request.POST.get('total', 1))
        percentage = (score / total) * 100
        if percentage >= 80:
            request.session['chap1_coursework_unlocked'] = True
        return render(request, 'myapp/result1.html', {
            'score': score,
            'total': total,
            'percentage': round(percentage),
            'passed': percentage >= 80,
        })
    return redirect('ass1')


def submit_coursework(request):
    if request.method == 'POST':
        submission = request.FILES.get('submission')
        if submission:
            # TODO: save file to storage
            messages.success(request, '✅ Assignment submitted successfully!')
        return redirect('chap1')
    return redirect('chap1')
def view_agreement(request):
    if request.session.get('role') != 'agent':
        return redirect('login_select')
    username = request.session.get('username')
    agreement = agreements_collection.find_one({'username': username})
    agreement_date = agreement.get('date', 'N/A') if agreement else 'N/A'
    return render(request, 'myapp/view_agreement.html', {
        'username': username,
        'agreement_date': agreement_date,
    })