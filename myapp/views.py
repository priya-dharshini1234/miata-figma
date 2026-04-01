from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
import bcrypt
import json

db = settings.MONGO_DB
users_collection      = db['users']
units_collection      = db['course_units']
agreements_collection = db['agreements']


# ─────────────────────────────────────────────
#  PUBLIC PAGES
# ─────────────────────────────────────────────

def index(request):
    return render(request, 'myapp/index.html')

def apply(request):
    return render(request, 'myapp/apply.html')

def faq(request):
    return render(request, 'myapp/faq.html')


# ─────────────────────────────────────────────
#  LOGIN / LOGOUT
# ─────────────────────────────────────────────

def login(request):
    return render(request, 'myapp/login.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = users_collection.find_one({'username': username, 'role': 'admin'})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            request.session['username'] = username
            request.session['role'] = 'admin'
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid admin credentials.')

    return render(request, 'myapp/admin_login.html')

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


# ─────────────────────────────────────────────
#  AGENT
# ─────────────────────────────────────────────

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
        'username':      username,
        'students':      students,
        'active_count':  active_count,
        'pending_count': pending_count,
    })

def view_agreement(request):
    if request.session.get('role') != 'agent':
        return redirect('login_select')
    username = request.session.get('username')
    agreement = agreements_collection.find_one({'username': username})
    agreement_date = agreement.get('date', 'N/A') if agreement else 'N/A'
    return render(request, 'myapp/view_agreement.html', {
        'username':       username,
        'agreement_date': agreement_date,
    })


# ─────────────────────────────────────────────
#  STUDENT DASHBOARD
# ─────────────────────────────────────────────

# Map unit order → Django URL name (add chap2, chap3 when ready)
UNIT_URLS = {
    0: 'chap1',
}

def student_dashboard(request):
    if request.session.get('role') != 'student':
        return redirect('login_select')

    username = request.session.get('username')
    units = list(units_collection.find({}).sort('order', 1))

    for unit in units:
        unit['_id'] = str(unit['_id'])
        order = unit.get('order', 99)
        # Always resolve URL from named route — never rely on DB stored url field
        if order in UNIT_URLS and not unit.get('locked', False):
            unit['url'] = reverse(UNIT_URLS[order])
        else:
            unit['url'] = '#'

    return render(request, 'myapp/dashboard_student.html', {
        'username': username,
        'units':    units,
    })


# ─────────────────────────────────────────────
#  PROFESSOR DASHBOARD
# ─────────────────────────────────────────────

def professor_dashboard(request):
    if request.session.get('role') != 'professor':
        return redirect('login_select')

    username = request.session.get('username')
    units = list(units_collection.find({}).sort('order', 1))
    for unit in units:
        unit['id']   = str(unit['_id'])
        unit['_id']  = str(unit['_id'])
        unit['assessment_count'] = len(unit.get('questions', []))

    student_count    = users_collection.count_documents({'role': 'student'})
    assessment_count = sum(u.get('assessment_count', 0) for u in units)
    submission_count = 0

    return render(request, 'myapp/dashboard_professor.html', {
        'username':         username,
        'units':            units,
        'student_count':    student_count,
        'assessment_count': assessment_count,
        'submission_count': submission_count,
    })


# ─────────────────────────────────────────────
#  UPDATE UNIT
# ─────────────────────────────────────────────

def update_unit(request):
    if request.session.get('role') != 'professor':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        from bson import ObjectId
        data    = json.loads(request.body)
        unit_id = data.get('unit_id')
        index   = data.get('index', 0)

        update_doc = {
            'title':                   data.get('title', ''),
            'description':             data.get('description', ''),
            'icon':                    data.get('icon', ''),
            'header_description':      data.get('header_description', ''),
            'video_title':             data.get('video_title', 'Lecture Video'),
            'video_duration':          data.get('video_duration', ''),
            'video_url':               data.get('video_url', ''),
            'pdf_title':               data.get('pdf_title', 'Study Material'),
            'pdf_subtitle':            data.get('pdf_subtitle', 'Reading Material'),
            'pdf_url':                 data.get('pdf_url', ''),
            'assessment_title':        data.get('assessment_title', 'Assessment'),
            'assessment_subtitle':     data.get('assessment_subtitle', 'Quiz Evaluation'),
            'passing_score':           int(data.get('passing_score', 60)),
            'questions':               data.get('questions', []),
            'coursework_enabled':      bool(data.get('coursework_enabled', False)),
            'coursework_title':        data.get('coursework_title', 'Course Work Submission'),
            'coursework_hours':        int(data.get('coursework_hours', 24)),
            'coursework_instructions': data.get('coursework_instructions', ''),
            'order':                   index,
        }

        if unit_id:
            units_collection.update_one(
                {'_id': ObjectId(unit_id)},
                {'$set': update_doc}
            )
        else:
            update_doc['locked'] = False
            update_doc['url']    = '#'
            units_collection.insert_one(update_doc)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ─────────────────────────────────────────────
#  CHAPTER 1
# ─────────────────────────────────────────────

def chap1(request):
    if request.session.get('role') != 'student':
        return redirect('login_select')

    unit = units_collection.find_one({'order': 0})
    if not unit:
        unit = units_collection.find_one({})

    coursework_enabled = False
    if unit:
        coursework_enabled = (
            unit.get('coursework_enabled', False) or
            request.session.get('chap1_coursework_unlocked', False)
        )

    unit_data = {
        'title':                   (unit or {}).get('title',                  'Chapter 1: Basic Abdominal Ultrasound Imaging'),
        'header_description':      (unit or {}).get('header_description',     'Introduction to abdominal ultrasound principles, anatomy and scanning techniques.'),
        'video_title':             (unit or {}).get('video_title',            'Lecture Video'),
        'video_duration':          (unit or {}).get('video_duration',         '15 minutes'),
        'video_url':               (unit or {}).get('video_url',              ''),
        'pdf_title':               (unit or {}).get('pdf_title',              'Study Material'),
        'pdf_subtitle':            (unit or {}).get('pdf_subtitle',           'Reading Material'),
        'pdf_url':                 (unit or {}).get('pdf_url',                ''),
        'assessment_title':        (unit or {}).get('assessment_title',       'Assessment'),
        'assessment_subtitle':     (unit or {}).get('assessment_subtitle',    'Quiz Evaluation'),
        'coursework_title':        (unit or {}).get('coursework_title',       'Course Work Submission'),
        'coursework_hours':        (unit or {}).get('coursework_hours',       24),
        'coursework_instructions': (unit or {}).get('coursework_instructions',''),
    }

    return render(request, 'myapp/chap1.html', {
        'username':           request.session.get('username'),
        'coursework_enabled': coursework_enabled,
        'unit':               unit_data,
    })


# ─────────────────────────────────────────────
#  ASSESSMENT 1
# ─────────────────────────────────────────────

def ass1(request):
    if request.session.get('role') != 'student':
        return redirect('login_select')

    unit = units_collection.find_one({'order': 0})
    questions     = []
    passing_score = 60
    if unit:
        questions     = unit.get('questions', [])
        passing_score = unit.get('passing_score', 60)

    return render(request, 'myapp/ass1.html', {
        'username':      request.session.get('username'),
        'questions':     questions,
        'passing_score': passing_score,
    })


# ─────────────────────────────────────────────
#  RESULT 1
# ─────────────────────────────────────────────

def result1(request):
    if request.method == 'POST':
        score      = int(request.POST.get('score', 0))
        total      = int(request.POST.get('total', 1))
        percentage = (score / total) * 100 if total else 0

        unit = units_collection.find_one({'order': 0})
        passing_score = unit.get('passing_score', 60) if unit else 60

        passed = percentage >= passing_score
        if passed:
            request.session['chap1_coursework_unlocked'] = True

        return render(request, 'myapp/result1.html', {
            'score':         score,
            'total':         total,
            'percentage':    round(percentage),
            'passed':        passed,
            'passing_score': passing_score,
        })
    return redirect('ass1')


# ─────────────────────────────────────────────
#  COURSEWORK SUBMISSION
# ─────────────────────────────────────────────

def submit_coursework(request):
    if request.method == 'POST':
        submission = request.FILES.get('submission')
        if submission:
            messages.success(request, '✅ Assignment submitted successfully!')
        return redirect('chap1')
    return redirect('chap1')


# ─────────────────────────────────────────────
#  INIT UNITS — visit /init-units/ ONCE to seed
#  MongoDB, then you can remove this view
# ─────────────────────────────────────────────

def init_units(request):
    if units_collection.count_documents({}) == 0:
        units_collection.insert_many([
            {
                'title': 'Unit 1 – Basic Abdominal Ultrasound',
                'description': 'Introduction to abdominal anatomy and scanning protocols.',
                'icon': 'fas fa-book-medical',
                'locked': False,
                'order': 0,
                'header_description': 'Introduction to abdominal ultrasound principles, anatomy and scanning techniques.',
                'video_title': 'Lecture Video',
                'video_duration': '15 minutes',
                'video_url': '',
                'pdf_title': 'Study Material',
                'pdf_subtitle': 'Reading Material',
                'pdf_url': '',
                'assessment_title': 'Assessment',
                'assessment_subtitle': 'Quiz Evaluation',
                'passing_score': 60,
                'questions': [],
                'coursework_enabled': False,
                'coursework_title': 'Course Work Submission',
                'coursework_hours': 24,
                'coursework_instructions': '',
            },
            {
                'title': 'Unit 2 – Obstetric Ultrasound',
                'description': 'Fetal development, measurements, and safety standards.',
                'icon': 'fas fa-heartbeat',
                'locked': True,
                'order': 1,
                'header_description': '',
                'video_title': 'Lecture Video', 'video_duration': '',
                'video_url': '', 'pdf_title': 'Study Material',
                'pdf_subtitle': 'Reading Material', 'pdf_url': '',
                'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
                'passing_score': 60, 'questions': [],
                'coursework_enabled': False, 'coursework_title': 'Course Work Submission',
                'coursework_hours': 24, 'coursework_instructions': '',
            },
            {
                'title': 'Unit 3 – Vascular Imaging',
                'description': 'Doppler techniques and vascular assessment procedures.',
                'icon': 'fas fa-x-ray',
                'locked': True,
                'order': 2,
                'header_description': '',
                'video_title': 'Lecture Video', 'video_duration': '',
                'video_url': '', 'pdf_title': 'Study Material',
                'pdf_subtitle': 'Reading Material', 'pdf_url': '',
                'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
                'passing_score': 60, 'questions': [],
                'coursework_enabled': False, 'coursework_title': 'Course Work Submission',
                'coursework_hours': 24, 'coursework_instructions': '',
            },
        ])
    return redirect('student_dashboard')
def admin_dashboard(request):
    if request.session.get('role') != 'admin':
        return redirect('login_select')

    students = list(users_collection.find({'role': 'student'}))
    for s in students:
        s['_id'] = str(s['_id'])
        s['status'] = s.get('status', 'pending')
        s['submittedAt'] = str(s.get('_id'))

    return render(request, 'myapp/admin_dashboard.html', {  # ✅ template path
        'applications': students
    })