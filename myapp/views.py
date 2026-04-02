from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
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
#  INIT UNITS
# ─────────────────────────────────────────────

def init_units(request):
    units_collection.delete_many({})
    units_collection.insert_many([
        {
            'title': 'Unit 1 – Basic Abdominal Ultrasound',
            'description': 'Introduction to abdominal anatomy and scanning protocols.',
            'icon': 'fas fa-book-medical',
            'locked': False, 'order': 0,
            'header_description': 'Introduction to abdominal ultrasound principles, anatomy and scanning techniques.',
            'video_title': 'Lecture Video', 'video_duration': '15 minutes',
            'video_url': '', 'pdf_title': 'Study Material',
            'pdf_subtitle': 'Reading Material', 'pdf_url': '',
            'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [],
            'coursework_enabled': False, 'coursework_title': 'Course Work Submission',
            'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 2 – Obstetric Ultrasound',
            'description': 'Fetal development, measurements, and safety standards.',
            'icon': 'fas fa-heartbeat',
            'locked': True, 'order': 1,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 3 – Vascular Imaging',
            'description': 'Doppler techniques and vascular assessment procedures.',
            'icon': 'fas fa-x-ray',
            'locked': True, 'order': 2,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 4 – Small Parts Ultrasound',
            'description': 'Thyroid, breast, and musculoskeletal high-resolution scanning.',
            'icon': 'fas fa-microscope',
            'locked': True, 'order': 3,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 5 – Cardiac Ultrasound (Echocardiography)',
            'description': 'Cardiac anatomy, ventricular function, and basic echo views.',
            'icon': 'fas fa-heart',
            'locked': True, 'order': 4,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 6 – Ultrasound Physics & Instrumentation',
            'description': 'Sound wave principles, transducer types, and image optimisation.',
            'icon': 'fas fa-wave-square',
            'locked': True, 'order': 5,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 7 – Gynaecological Ultrasound',
            'description': 'Uterus, ovary pathology, and transvaginal scanning techniques.',
            'icon': 'fas fa-venus',
            'locked': True, 'order': 6,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 8 – Paediatric Ultrasound',
            'description': 'Age-specific protocols, neonatal brain, and hip assessments.',
            'icon': 'fas fa-child',
            'locked': True, 'order': 7,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 9 – Interventional & Guided Procedures',
            'description': 'Ultrasound-guided biopsies, aspirations, and drainage techniques.',
            'icon': 'fas fa-syringe',
            'locked': True, 'order': 8,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
        {
            'title': 'Unit 10 – Professional Practice & Reporting',
            'description': 'Ethics, medicolegal responsibilities, and structured report writing.',
            'icon': 'fas fa-file-medical-alt',
            'locked': True, 'order': 9,
            'header_description': '', 'video_title': 'Lecture Video', 'video_duration': '',
            'video_url': '', 'pdf_title': 'Study Material', 'pdf_subtitle': 'Reading Material',
            'pdf_url': '', 'assessment_title': 'Assessment', 'assessment_subtitle': 'Quiz Evaluation',
            'passing_score': 60, 'questions': [], 'coursework_enabled': False,
            'coursework_title': 'Course Work Submission', 'coursework_hours': 24, 'coursework_instructions': '',
        },
    ])
    return redirect('student_dashboard')


# ─────────────────────────────────────────────
#  ADMIN DASHBOARD
# ─────────────────────────────────────────────

def admin_dashboard(request):
    if request.session.get('role') != 'admin':
        return redirect('login_select')

    students = list(users_collection.find({'role': 'student'}))
    for s in students:
        s['_id']        = str(s['_id'])
        s['status']     = s.get('status', 'pending')
        s['submittedAt'] = s.get('submitted_at', str(s['_id']))
        # Ensure docs is always a dict so the dashboard never sees undefined
        if 'docs' not in s or not isinstance(s.get('docs'), dict):
            s['docs'] = {k: [] for k in FILE_FIELDS}

    return render(request, 'myapp/admin_dashboard.html', {
        'applications': students
    })


# ─────────────────────────────────────────────
#  EMAIL CONSTANTS & HELPERS
# ─────────────────────────────────────────────

REQUIRED_FIELDS = ['ref_number', 'full_name', 'email', 'phone', 'country', 'sop']

FILE_FIELDS = [
    'ug_certificate', 'transcripts', 'passport',
    'cv', 'english_proof', 'references', 'work_experience',
]

FIELD_LABELS = {
    'ug_certificate':  'UG Degree Certificate',
    'transcripts':     'Academic Transcripts',
    'passport':        'Passport',
    'cv':              'CV / Resume',
    'english_proof':   'English Proficiency Proof',
    'references':      'Reference Letters',
    'work_experience': 'Work Experience Certificates',
}

# ── Email that goes to the student on submission ───────────────────────────────

def _build_student_html(data: dict, doc_summary: dict) -> str:
    doc_rows = ''.join(
        f'<tr><td style="padding:6px 12px;color:#4a5f78;font-size:13px;">{FIELD_LABELS[k]}</td>'
        f'<td style="padding:6px 12px;color:#1a9e8f;font-size:13px;">{", ".join(v) or "—"}</td></tr>'
        for k, v in doc_summary.items()
    )
    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <tr><td style="background:linear-gradient(135deg,#0a1f35,#0f2f4f);padding:36px 40px;text-align:center;">
          <div style="display:inline-block;background:linear-gradient(135deg,#1a9e8f,#0d7a6d);border-radius:10px;width:44px;height:44px;line-height:44px;text-align:center;font-weight:700;font-size:20px;color:white;margin-bottom:14px;">M</div>
          <h1 style="color:#ffffff;font-size:22px;margin:0 0 6px;">Application Received</h1>
          <p style="color:rgba(255,255,255,0.55);font-size:13px;margin:0;">MIATA Medical Imaging Academy</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="font-size:15px;color:#0a1f35;margin:0 0 8px;">Dear <strong>{data['full_name']}</strong>,</p>
          <p style="font-size:14px;color:#4a5f78;line-height:1.7;margin:0 0 24px;">
            Thank you for applying to MIATA's Diagnostic Ultrasound Programme. We have successfully received your application and our admissions team will be in touch within <strong>24 hours</strong>.
          </p>
          <div style="background:#f0faf9;border:1px solid rgba(26,158,143,0.25);border-radius:10px;padding:14px 20px;margin-bottom:24px;text-align:center;">
            <span style="font-size:11px;color:#8fa3b3;letter-spacing:1px;text-transform:uppercase;">Your Reference Number</span><br>
            <span style="font-size:20px;font-weight:700;color:#1a9e8f;">{data['ref_number']}</span>
          </div>
          <p style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#8fa3b3;margin:0 0 10px;">Application Summary</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eef2f7;border-radius:10px;overflow:hidden;margin-bottom:24px;">
            <tr style="background:#f8fbfa;"><td style="padding:8px 12px;font-size:12px;font-weight:600;color:#8fa3b3;width:40%;">Full Name</td><td style="padding:8px 12px;font-size:13px;color:#0a1f35;">{data['full_name']}</td></tr>
            <tr><td style="padding:8px 12px;font-size:12px;font-weight:600;color:#8fa3b3;">Email</td><td style="padding:8px 12px;font-size:13px;color:#0a1f35;">{data['email']}</td></tr>
            <tr style="background:#f8fbfa;"><td style="padding:8px 12px;font-size:12px;font-weight:600;color:#8fa3b3;">Phone</td><td style="padding:8px 12px;font-size:13px;color:#0a1f35;">{data['phone']}</td></tr>
            <tr><td style="padding:8px 12px;font-size:12px;font-weight:600;color:#8fa3b3;">Country</td><td style="padding:8px 12px;font-size:13px;color:#0a1f35;">{data['country']}</td></tr>
            {'<tr style="background:#f8fbfa;"><td style="padding:8px 12px;font-size:12px;font-weight:600;color:#8fa3b3;">Agent</td><td style="padding:8px 12px;font-size:13px;color:#0a1f35;">' + str(data.get("agent_name","")) + ' (' + str(data.get("agent_contact","")) + ')</td></tr>' if data.get('agent_name') else ''}
          </table>
          <p style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#8fa3b3;margin:0 0 10px;">Documents Submitted</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eef2f7;border-radius:10px;overflow:hidden;margin-bottom:28px;">
            {doc_rows}
          </table>
          <p style="font-size:13px;color:#4a5f78;line-height:1.7;margin:0 0 6px;">
            If you have any questions, reply to this email or contact us at:<br>
            <a href="mailto:admissions@miataedu.org" style="color:#1a9e8f;">admissions@miataedu.org</a> &nbsp;·&nbsp;
            <a href="tel:+919927829520" style="color:#1a9e8f;">+91 99278 29520</a>
          </p>
        </td></tr>
        <tr><td style="background:#f8fbfa;border-top:1px solid #eef2f7;padding:20px 40px;text-align:center;">
          <p style="font-size:11px;color:#9baab8;margin:0;">© 2026 MIATA Medical Imaging Academy · All rights reserved</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ── Email that goes to the admin team on submission ────────────────────────────

def _build_admin_html(data: dict, doc_summary: dict) -> str:
    doc_rows = ''.join(
        f'<tr><td style="padding:5px 10px;font-size:12px;color:#4a5f78;">{FIELD_LABELS[k]}</td>'
        f'<td style="padding:5px 10px;font-size:12px;color:#0a1f35;">{", ".join(v) or "—"}</td></tr>'
        for k, v in doc_summary.items()
    )
    sop_preview = (data.get('sop', '') or '')[:400]
    return f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;padding:24px;">
  <h2 style="color:#0a1f35;">📋 New MIATA Application — {data['ref_number']}</h2>
  <table cellpadding="0" cellspacing="4" style="margin-bottom:16px;">
    <tr><td style="font-weight:600;width:160px;">Name</td><td>{data['full_name']}</td></tr>
    <tr><td style="font-weight:600;">Email</td><td>{data['email']}</td></tr>
    <tr><td style="font-weight:600;">Phone</td><td>{data['phone']}</td></tr>
    <tr><td style="font-weight:600;">Country</td><td>{data['country']}</td></tr>
    <tr><td style="font-weight:600;">Agent</td><td>{data.get('agent_name') or '—'} / {data.get('agent_contact') or '—'}</td></tr>
    <tr><td style="font-weight:600;">Submitted</td><td>{data.get('submitted_at','')}</td></tr>
  </table>
  <h4 style="color:#1a9e8f;margin-bottom:6px;">Documents</h4>
  <table cellpadding="0" cellspacing="2" style="margin-bottom:16px;">{doc_rows}</table>
  <h4 style="color:#1a9e8f;margin-bottom:6px;">Statement of Purpose</h4>
  <p style="background:#f5f5f5;padding:12px;border-radius:6px;font-size:13px;line-height:1.6;">{sop_preview}{'…' if len(data.get('sop',''))>400 else ''}</p>
  <p style="font-size:11px;color:#9baab8;">This is an automated notification from the MIATA registration system.</p>
</body></html>
"""


# ── Email sent to student when their application is ACCEPTED ──────────────────

def _build_accepted_html(full_name: str, ref_number: str, note: str = '') -> str:
    note_block = f"""
      <div style="background:#f0faf9;border-left:4px solid #1a9e8f;border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:28px;">
        <p style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#1a9e8f;margin:0 0 6px;">Message from Admissions</p>
        <p style="font-size:13px;color:#4a5f78;line-height:1.7;margin:0;">{note}</p>
      </div>
    """ if note.strip() else ''

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Header — green acceptance banner -->
        <tr><td style="background:linear-gradient(135deg,#064e3b,#065f46);padding:40px;text-align:center;">
          <div style="width:72px;height:72px;background:rgba(255,255,255,0.12);border-radius:50%;display:inline-flex;align-items:center;justify-content:center;margin-bottom:18px;">
            <span style="font-size:36px;">🎉</span>
          </div>
          <h1 style="color:#ffffff;font-size:26px;margin:0 0 8px;font-family:Georgia,serif;">Congratulations!</h1>
          <p style="color:rgba(255,255,255,0.75);font-size:14px;margin:0;">Your application has been accepted</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:36px 40px;">
          <p style="font-size:15px;color:#0a1f35;margin:0 0 12px;">Dear <strong>{full_name}</strong>,</p>
          <p style="font-size:14px;color:#4a5f78;line-height:1.75;margin:0 0 24px;">
            We are delighted to inform you that your application to <strong>MIATA's Diagnostic Ultrasound Programme</strong>
            has been <strong style="color:#059669;">accepted</strong>. Welcome to the MIATA family!
          </p>

          <!-- Ref badge -->
          <div style="background:#f0faf9;border:1px solid rgba(26,158,143,0.25);border-radius:10px;padding:14px 20px;margin-bottom:24px;text-align:center;">
            <span style="font-size:11px;color:#8fa3b3;letter-spacing:1px;text-transform:uppercase;">Reference Number</span><br>
            <span style="font-size:20px;font-weight:700;color:#1a9e8f;">{ref_number}</span>
          </div>

          {note_block}

          <!-- Next steps -->
          <p style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#8fa3b3;margin:0 0 14px;">Your Next Steps</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr>
              <td style="padding:10px 14px;background:#f8fbfa;border:1px solid #eef2f7;border-radius:10px 10px 0 0;">
                <span style="font-size:13px;color:#059669;font-weight:700;">Step 1 &nbsp;·</span>
                <span style="font-size:13px;color:#4a5f78;"> Our admissions team will contact you shortly with onboarding details.</span>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 14px;background:#ffffff;border:1px solid #eef2f7;border-top:none;">
                <span style="font-size:13px;color:#059669;font-weight:700;">Step 2 &nbsp;·</span>
                <span style="font-size:13px;color:#4a5f78;"> Complete the enrolment formalities and fee payment as communicated.</span>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 14px;background:#f8fbfa;border:1px solid #eef2f7;border-top:none;border-radius:0 0 10px 10px;">
                <span style="font-size:13px;color:#059669;font-weight:700;">Step 3 &nbsp;·</span>
                <span style="font-size:13px;color:#4a5f78;"> Access your student portal and begin your learning journey.</span>
              </td>
            </tr>
          </table>

          <p style="font-size:13px;color:#4a5f78;line-height:1.7;margin:0;">
            For any queries, reach us at:<br>
            <a href="mailto:admissions@miataedu.org" style="color:#1a9e8f;">admissions@miataedu.org</a> &nbsp;·&nbsp;
            <a href="tel:+919927829520" style="color:#1a9e8f;">+91 99278 29520</a>
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f8fbfa;border-top:1px solid #eef2f7;padding:20px 40px;text-align:center;">
          <p style="font-size:11px;color:#9baab8;margin:0;">© 2026 MIATA Medical Imaging Academy · All rights reserved</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ── Email sent to student when their application is REJECTED ──────────────────

def _build_rejected_html(full_name: str, ref_number: str, note: str = '') -> str:
    note_block = f"""
      <div style="background:#fff8f8;border-left:4px solid #e05252;border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:28px;">
        <p style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#e05252;margin:0 0 6px;">Message from Admissions</p>
        <p style="font-size:13px;color:#4a5f78;line-height:1.7;margin:0;">{note}</p>
      </div>
    """ if note.strip() else ''

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Header — neutral dark banner -->
        <tr><td style="background:linear-gradient(135deg,#0a1f35,#1c2e3f);padding:40px;text-align:center;">
          <div style="display:inline-block;background:linear-gradient(135deg,#1a9e8f,#0d7a6d);border-radius:10px;width:44px;height:44px;line-height:44px;text-align:center;font-weight:700;font-size:20px;color:white;margin-bottom:16px;">M</div>
          <h1 style="color:#ffffff;font-size:22px;margin:0 0 6px;font-family:Georgia,serif;">Application Update</h1>
          <p style="color:rgba(255,255,255,0.55);font-size:13px;margin:0;">MIATA Medical Imaging Academy</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:36px 40px;">
          <p style="font-size:15px;color:#0a1f35;margin:0 0 12px;">Dear <strong>{full_name}</strong>,</p>
          <p style="font-size:14px;color:#4a5f78;line-height:1.75;margin:0 0 24px;">
            Thank you for your interest in MIATA's Diagnostic Ultrasound Programme and for taking the time
            to submit your application. After careful review, we regret to inform you that we are unable to
            offer you a place in the current intake.
          </p>

          <!-- Ref badge -->
          <div style="background:#fafafa;border:1px solid #e8ecf0;border-radius:10px;padding:14px 20px;margin-bottom:24px;text-align:center;">
            <span style="font-size:11px;color:#8fa3b3;letter-spacing:1px;text-transform:uppercase;">Reference Number</span><br>
            <span style="font-size:18px;font-weight:700;color:#6b7c8f;">{ref_number}</span>
          </div>

          {note_block}

          <p style="font-size:14px;color:#4a5f78;line-height:1.75;margin:0 0 24px;">
            This decision does not preclude you from applying to a future intake. We encourage you to
            reapply once you have had the opportunity to address any areas highlighted by our admissions team.
          </p>

          <p style="font-size:13px;color:#4a5f78;line-height:1.7;margin:0;">
            If you have any questions or would like feedback, please contact:<br>
            <a href="mailto:admissions@miataedu.org" style="color:#1a9e8f;">admissions@miataedu.org</a> &nbsp;·&nbsp;
            <a href="tel:+919927829520" style="color:#1a9e8f;">+91 99278 29520</a>
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f8fbfa;border-top:1px solid #eef2f7;padding:20px 40px;text-align:center;">
          <p style="font-size:11px;color:#9baab8;margin:0;">© 2026 MIATA Medical Imaging Academy · All rights reserved</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ─────────────────────────────────────────────
#  REGISTRATION VIEW   POST /api/register/
# ─────────────────────────────────────────────

@csrf_exempt
@require_POST
def register(request):
    try:
        # 1. Validate required fields
        missing = [f for f in REQUIRED_FIELDS if not request.POST.get(f, '').strip()]
        if missing:
            return JsonResponse({'ok': False, 'message': f'Missing fields: {", ".join(missing)}'}, status=400)

        # 2. Collect data
        from datetime import datetime, timezone
        data = {
            'ref_number':    request.POST.get('ref_number'),
            'full_name':     request.POST.get('full_name'),
            'email':         request.POST.get('email'),
            'phone':         request.POST.get('phone'),
            'country':       request.POST.get('country'),
            'agent_name':    request.POST.get('agent_name', ''),
            'agent_contact': request.POST.get('agent_contact', ''),
            'sop':           request.POST.get('sop', ''),
            'submitted_at':  datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC'),
        }

        # 3. File summary (names only — files are not stored server-side here)
        doc_summary = {k: [f.name for f in request.FILES.getlist(k)] for k in FILE_FIELDS}

        # 4. Save to MongoDB — include docs so admin dashboard can display filenames
        try:
            users_collection.insert_one({
                **data,
                'docs':   doc_summary,   # ← file names keyed by field name
                'role':   'student',
                'status': 'pending',
            })
        except Exception as db_error:
            print("DB ERROR:", str(db_error))

        # 5. Email → Student (confirmation of submission)
        try:
            msg = EmailMultiAlternatives(
                subject=f"[MIATA] Application Received — {data['ref_number']}",
                body=f"Dear {data['full_name']}, your application has been received. Ref: {data['ref_number']}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[data['email']],
            )
            msg.attach_alternative(_build_student_html(data, doc_summary), 'text/html')
            msg.send(fail_silently=False)
        except Exception as e:
            print("STUDENT EMAIL ERROR:", str(e))

        # 6. Email → Admin team (new application notification)
        try:
            admin_addr = getattr(settings, 'ADMISSIONS_EMAIL', 'admissions@miataedu.org')
            msg = EmailMultiAlternatives(
                subject=f"[MIATA] New Application — {data['ref_number']}",
                body="New application received.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[admin_addr],
                reply_to=[data['email']],
            )
            msg.attach_alternative(_build_admin_html(data, doc_summary), 'text/html')
            msg.send(fail_silently=True)
        except Exception as e:
            print("ADMIN EMAIL ERROR:", str(e))

        return JsonResponse({'ok': True, 'message': 'Application submitted successfully!', 'ref': data['ref_number']})

    except Exception as e:
        print("REGISTER ERROR:", str(e))
        return JsonResponse({'ok': False, 'message': 'Something went wrong. Please try again.'}, status=500)


# ─────────────────────────────────────────────
#  STATUS UPDATE VIEW   POST /api/update-status/
#  Called by admin_dashboard.html when the admin
#  clicks Accept / Reject (or any other status).
#  Sends an email to the student for accepted /
#  rejected decisions only.
# ─────────────────────────────────────────────

@csrf_exempt
@require_POST
def update_status(request):
    """
    Expected JSON body:
    {
        "ref_id":    "MIATA-2026-1001",   // the application ref / id field
        "status":    "accepted",           // pending | reviewing | accepted | rejected
        "note":      "Optional admin note shown in the email"
    }
    """
    try:
        body      = json.loads(request.body)
        ref_id    = body.get('ref_id', '').strip()
        new_status = body.get('status', '').strip().lower()
        note      = body.get('note', '').strip()

        if not ref_id or not new_status:
            return JsonResponse({'ok': False, 'message': 'ref_id and status are required.'}, status=400)

        if new_status not in ('pending', 'reviewing', 'accepted', 'rejected'):
            return JsonResponse({'ok': False, 'message': f'Invalid status: {new_status}'}, status=400)

        # ── Find applicant in MongoDB ────────────────────────────────────────
        applicant = users_collection.find_one({'ref_number': ref_id, 'role': 'student'})
        if not applicant:
            # Fallback: some records may use the Mongo _id string as ref
            from bson import ObjectId
            try:
                applicant = users_collection.find_one({'_id': ObjectId(ref_id), 'role': 'student'})
            except Exception:
                pass

        if not applicant:
            return JsonResponse({'ok': False, 'message': f'No applicant found for ref: {ref_id}'}, status=404)

        student_email = applicant.get('email', '')
        full_name     = applicant.get('full_name', 'Applicant')
        ref_number    = applicant.get('ref_number', ref_id)

        # ── Update status in MongoDB ─────────────────────────────────────────
        from datetime import datetime, timezone
        users_collection.update_one(
            {'_id': applicant['_id']},
            {'$set': {'status': new_status}}
        )

        # ── Send email only for accepted / rejected ──────────────────────────
        email_sent = False
        if new_status in ('accepted', 'rejected') and student_email:
            try:
                if new_status == 'accepted':
                    subject   = f"[MIATA] 🎉 Application Accepted — {ref_number}"
                    html_body = _build_accepted_html(full_name, ref_number, note)
                    plain     = f"Dear {full_name}, congratulations! Your MIATA application ({ref_number}) has been accepted."
                else:
                    subject   = f"[MIATA] Application Update — {ref_number}"
                    html_body = _build_rejected_html(full_name, ref_number, note)
                    plain     = f"Dear {full_name}, we regret to inform you that your MIATA application ({ref_number}) was not successful at this time."

                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[student_email],
                )
                msg.attach_alternative(html_body, 'text/html')
                msg.send(fail_silently=False)
                email_sent = True
            except Exception as e:
                print(f"STATUS EMAIL ERROR ({new_status}):", str(e))

        return JsonResponse({
            'ok':        True,
            'message':   f'Status updated to {new_status}.',
            'email_sent': email_sent,
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'Invalid JSON body.'}, status=400)
    except Exception as e:
        print("UPDATE STATUS ERROR:", str(e))
        return JsonResponse({'ok': False, 'message': 'Something went wrong.'}, status=500)