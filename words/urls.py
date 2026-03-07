from django.urls import path
from . import views

urlpatterns = [
    # 登录相关
    path('', views.student_login, name='login'),
    path('student-login/', views.student_login, name='student_login'),
    path('teacher-login/', views.teacher_login, name='teacher_login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 学生学习
    path('dashboard/', views.dashboard, name='dashboard'),
    path('study/', views.study, name='study'),
    path('review/', views.review, name='review'),
    path('answer/<int:word_id>/', views.answer, name='answer'),
    path('ranking/', views.class_ranking, name='ranking'),
path('change-password/', views.change_password, name='change_password'),
    
    # 教师管理
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.student_management, name='student_management'),
    path('teacher/students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('teacher/students/update-class/<int:student_id>/', views.update_student_class, name='update_student_class'),
    path('teacher/students/import/', views.import_students, name='import_students'),
    path('teacher/words/', views.word_management, name='word_management'),
    path('teacher/words/add/', views.add_word, name='add_word'),
    path('teacher/homework/', views.homework_management, name='homework_management'),
    path('teacher/homework/create/', views.create_homework, name='create_homework'),
    path('teacher/change-password/', views.teacher_change_password, name='teacher_change_password'),
    path('teacher/classes/', views.class_management, name='class_management'),
    path('teacher/words/edit/<int:word_id>/', views.edit_word, name='edit_word'),
    path('teacher/words/delete/<int:word_id>/', views.delete_word, name='delete_word'),
]
