from django.urls import path
from myapp import views

urlpatterns = [
    path('',                     views.index,              name='home'),
    path('apply/',               views.apply,              name='apply'),
    path('login/',               views.login,              name='login_select'),
    path('login/student/',       views.login_student,      name='login_student'),
    path('login/admin/',         views.admin_login,        name='admin_login'),
    path('login/agent/',         views.login_agent,        name='login_agent'),
    path('login/professor/',     views.login_professor,    name='login_professor'),
    path('signup/',              views.signup,             name='signup'),
    path('logout/',              views.logout,             name='logout'),
    path('agent/agreement/',     views.agent_agreement,    name='agent_agreement'),
    path('student/dashboard/',   views.student_dashboard,  name='student_dashboard'),
    path('admin/dashboard/',     views.admin_dashboard,    name='admin_dashboard'),
    path('professor/dashboard/', views.professor_dashboard,name='professor_dashboard'),
    path('agent/dashboard/',     views.agent_dashboard,    name='agent_dashboard'),
    path('api/update-unit/',     views.update_unit,        name='update_unit'),
    path('chap1/',               views.chap1,              name='chap1'),
    path('chap1/assessment/',    views.ass1,               name='ass1'),
    path('chap1/result/',        views.result1,            name='result1'),
    path('chap1/submit/',        views.submit_coursework,  name='submit_coursework'),
    path('agent/agreement/view/',views.view_agreement,     name='view_agreement'),
    path('faq/',                 views.faq,                name='faq'),
]