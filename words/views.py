from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
from .models import Word, UserWord, DailyStats, UserProfile, Homework, HomeworkSubmission
from .decorators import teacher_required
import random
from datetime import datetime, timedelta

# ========== 学生登录（学号+班级） ==========
def student_login(request):
    """学生用班级+学号登录"""
    if request.method == 'POST':
        class_name = request.POST.get('class_name')
        student_id = request.POST.get('student_id')
        real_name = request.POST.get('real_name')
        
        # 查找用户：班级_学号 作为用户名
        username = f"{class_name}_{student_id}"
        user = authenticate(request, username=username, password=student_id)  # 初始密码是学号
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            # 如果不存在，自动创建（首次登录）
            try:
                user = User.objects.create_user(
                    username=username,
                    password=student_id,
                    first_name=real_name
                )
                UserProfile.objects.create(
                    user=user,
                    student_id=student_id,
                    class_name=class_name,
                    real_name=real_name
                )
                login(request, user)
                messages.success(request, f'欢迎{real_name}，首次登录已自动创建账号')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, '登录失败，请检查班级和学号')
    
    return render(request, 'words/student_login.html')

def teacher_login(request):
    """教师用传统方式登录"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and hasattr(user, 'userprofile') and user.userprofile.is_teacher:
            login(request, user)
            return redirect('teacher_dashboard')
        else:
            messages.error(request, '教师账号或密码错误')
    
    return render(request, 'words/teacher_login.html')

def logout_view(request):
    logout(request)
    return redirect('student_login')

# ========== 学生功能 ==========
@login_required
def dashboard(request):
    """学生仪表盘"""
    user = request.user
    today = timezone.now().date()
    
    # 今日作业
    try:
        homework = Homework.objects.filter(
            class_name=user.userprofile.class_name,
            is_active=True,
            due_date__gte=today
        ).first()
        
        hw_progress = None
        if homework:
            submission, _ = HomeworkSubmission.objects.get_or_create(
                homework=homework,
                student=user
            )
            total = homework.words.count()
            completed = UserWord.objects.filter(
                user=user,
                word__in=homework.words.all(),
                status='mastered'
            ).count()
            hw_progress = {
                'total': total,
                'completed': completed,
                'percent': int(completed/total*100) if total > 0 else 0
            }
    except:
        homework = None
        hw_progress = None
    
    # 统计数据
    due_count = UserWord.objects.filter(user=user, next_review__lte=timezone.now()).count()
    learned_count = UserWord.objects.filter(user=user, status='mastered').count()
    
    # 班级排名
    class_students = User.objects.filter(userprofile__class_name=user.userprofile.class_name)
    my_rank = list(class_students.annotate(
        mastered_count=Count('userword', filter=Q(userword__status='mastered'))
    ).order_by('-mastered_count').values_list('id', flat=True)).index(user.id) + 1 if user in class_students else 0
    
    context = {
        'homework': homework,
        'hw_progress': hw_progress,
        'due_count': due_count,
        'learned_count': learned_count,
        'my_rank': my_rank,
        'class_total': class_students.count()
    }
    return render(request, 'words/dashboard.html', context)

@login_required
def study(request):
    """学习模式：优先做作业，其次复习"""
    user = request.user
    
    # 检查是否有未完成的作业
    today = timezone.now().date()
    homework = Homework.objects.filter(
        class_name=user.userprofile.class_name,
        is_active=True,
        due_date__gte=today
    ).first()
    
    if homework:
        # 找作业中未掌握的单词
        hw_words = homework.words.exclude(
            id__in=UserWord.objects.filter(user=user, status='mastered').values_list('word_id', flat=True)
        )
        if hw_words.exists():
            word = random.choice(list(hw_words))
            return render(request, 'words/study.html', {
                'word': word,
                'mode': 'homework',
                'homework': homework
            })
    
    # 正常学习新词
    existing = UserWord.objects.filter(user=user).values_list('word_id', flat=True)
    new_words = Word.objects.exclude(id__in=existing)[:10]
    
    if not new_words:
        return redirect('review')
    
    word = random.choice(list(new_words))
    return render(request, 'words/study.html', {'word': word, 'mode': 'learning'})

@login_required
def review(request):
    """复习模式"""
    user = request.user
    due = UserWord.objects.filter(
        user=user,
        next_review__lte=timezone.now()
    ).select_related('word').first()
    
    if not due:
        return render(request, 'words/all_caught_up.html')
    
    return render(request, 'words/study.html', {
        'user_word': due,
        'word': due.word,
        'mode': 'review'
    })

@login_required
def answer(request, word_id):
    """使用 SM-2 算法的评分：1=没记住, 2=有点印象, 3=记住了"""
    if request.method == 'POST':
        # 将 1-3 分映射到 SM-2 的 0-5 分制
        quality_map = {1: 0, 2: 3, 3: 5}
        raw_quality = int(request.POST.get('quality', 2))
        quality = quality_map.get(raw_quality, 2)
        
        word = get_object_or_404(Word, id=word_id)
        
        user_word, created = UserWord.objects.get_or_create(
            user=request.user,
            word=word
        )
        
        # ✅ 使用 SM-2 算法计算下次复习时间
        from .utils import calculate_next_review
        interval = calculate_next_review(user_word, quality)
        
        # 根据质量更新状态（用于前端展示）
        if quality >= 4:  # 3分对应5分制
            user_word.status = 'mastered'
        elif quality >= 3:  # 2分对应3分制
            user_word.status = 'familiar'
        else:
            user_word.status = 'new'
        
        user_word.save()
        
        # 更新今日统计（区分新学和复习）
        today = timezone.now().date()
        stats, _ = DailyStats.objects.get_or_create(user=request.user, date=today)
        
        if created or user_word.total_reviews <= 1:
            # 新学单词
            stats.words_learned += 1
        else:
            # 复习单词
            stats.words_reviewed += 1
        stats.save()
        
        return JsonResponse({'success': True, 'interval': interval})
    
    return JsonResponse({'success': False})

@login_required
def class_ranking(request):
    """班级排行榜"""
    user = request.user
    class_name = user.userprofile.class_name
    
    students = User.objects.filter(
        userprofile__class_name=class_name,
        userprofile__is_teacher=False
    ).annotate(
        mastered_count=Count('userword', filter=Q(userword__status='mastered')),
        homework_done=Count('homeworksubmission')
    ).order_by('-mastered_count')[:20]
    
    return render(request, 'words/class_ranking.html', {
        'students': students,
        'my_id': user.id
    })

# ========== 教师功能 ==========
@login_required
@teacher_required
def teacher_dashboard(request):
    """教师控制台"""
    teacher = request.user
    classes = UserProfile.objects.filter(
        is_teacher=False
    ).values_list('class_name', flat=True).distinct()
    
    class_data = []
    for class_name in classes:
        if not class_name:
            continue
        students = User.objects.filter(userprofile__class_name=class_name)
        stats = {
            'name': class_name,
            'student_count': students.count(),
            'total_mastered': UserWord.objects.filter(
                user__in=students,
                status='mastered'
            ).count(),
            'active_homework': Homework.objects.filter(
                class_name=class_name,
                is_active=True
            ).count()
        }
        class_data.append(stats)
    
    return render(request, 'words/teacher/dashboard.html', {
        'classes': class_data
    })

@login_required
@teacher_required
def student_management(request):
    """学生管理"""
    teacher = request.user
    # 获取教师任教班级（从已有学生推断，或硬编码）
    classes = UserProfile.objects.filter(
        is_teacher=False
    ).values_list('class_name', flat=True).distinct()
    
    selected_class = request.GET.get('class', classes.first() if classes else '')
    
    students = User.objects.filter(
        userprofile__class_name=selected_class,
        userprofile__is_teacher=False
    ).annotate(
        mastered_count=Count('userword', filter=Q(userword__status='mastered'))
    )
    
    return render(request, 'words/teacher/student_management.html', {
        'students': students,
        'classes': classes,
        'selected_class': selected_class
    })

@login_required
@teacher_required
def delete_student(request, student_id):
    """删除学生账号（调试用）"""
    student = get_object_or_404(User, id=student_id)
    
    # 安全校验
    if student == request.user:
        messages.error(request, '不能删除自己')
        return redirect('student_management')
    
    if hasattr(student, 'userprofile') and student.userprofile.is_teacher:
        messages.error(request, '不能删除教师')
        return redirect('student_management')
    
    username = student.userprofile.real_name or student.username
    student.delete()
    messages.success(request, f'已删除学生 {username}')
    return redirect('student_management')

@login_required
@teacher_required
def word_management(request):
    """单词管理"""
    words = Word.objects.all().order_by('textbook', 'unit')
    return render(request, 'words/teacher/word_management.html', {'words': words})

@login_required
@teacher_required
def add_word(request):
    """添加单词"""
    if request.method == 'POST':
        Word.objects.create(
            word=request.POST.get('word'),
            pronunciation=request.POST.get('pronunciation'),
            definition=request.POST.get('definition'),
            example=request.POST.get('example'),
            unit=request.POST.get('unit', 'Unit 1'),
            textbook=request.POST.get('textbook', '课本'),
            is_core=request.POST.get('is_core') == 'on'
        )
        messages.success(request, '单词添加成功')
        return redirect('word_management')
    return render(request, 'words/teacher/add_word.html')

@login_required
@teacher_required
def homework_management(request):
    """作业管理"""
    homeworks = Homework.objects.filter(teacher=request.user).order_by('-created_at')
    return render(request, 'words/teacher/homework_list.html', {'homeworks': homeworks})

@login_required
@teacher_required
def create_homework(request):
    """创建作业"""
    if request.method == 'POST':
        hw = Homework.objects.create(
            teacher=request.user,
            class_name=request.POST.get('class_name'),
            title=request.POST.get('title'),
            due_date=request.POST.get('due_date')
        )
        # 添加单词到作业
        word_ids = request.POST.getlist('words')
        hw.words.set(word_ids)
        messages.success(request, '作业发布成功')
        return redirect('homework_management')
    
    classes = UserProfile.objects.filter(
        is_teacher=False
    ).values_list('class_name', flat=True).distinct()
    words = Word.objects.all()
    
    return render(request, 'words/teacher/create_homework.html', {
        'classes': classes,
        'words': words
    })

@login_required
@teacher_required
def import_students(request):
    """批量导入学生"""
    if request.method == 'POST':
        # 简单格式：班级,学号,姓名 每行一个
        data = request.POST.get('students_data', '')
        class_name = request.POST.get('class_name')
        
        lines = data.strip().split('\n')
        created_count = 0
        
        for line in lines:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                student_id = parts[0].strip()
                real_name = parts[1].strip() if len(parts) > 1 else student_id
                
                username = f"{class_name}_{student_id}"
                if not User.objects.filter(username=username).exists():
                    user = User.objects.create_user(
                        username=username,
                        password=student_id,  # 初始密码是学号
                        first_name=real_name
                    )
                    UserProfile.objects.create(
                        user=user,
                        student_id=student_id,
                        class_name=class_name,
                        real_name=real_name
                    )
                    created_count += 1
        
        messages.success(request, f'成功导入 {created_count} 名学生')
        return redirect('student_management')
    
    classes = UserProfile.objects.filter(
        is_teacher=False
    ).values_list('class_name', flat=True).distinct()
    
    return render(request, 'words/teacher/import_students.html', {
        'classes': classes
    })

# ========== 密码修改功能（新增） ==========

@login_required
def change_password(request):
    """学生修改密码"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # 验证旧密码
        if not request.user.check_password(old_password):
            messages.error(request, '旧密码错误，请重新输入')
            return redirect('change_password')
        
        # 验证新密码
        if new_password != confirm_password:
            messages.error(request, '两次输入的新密码不一致')
            return redirect('change_password')
        
        if len(new_password) < 6:
            messages.error(request, '新密码至少需要6位字符')
            return redirect('change_password')
        
        # 修改密码
        request.user.set_password(new_password)
        request.user.save()
        
        messages.success(request, '密码修改成功！请用新密码重新登录')
        return redirect('login')
    
    return render(request, 'words/change_password.html')

@login_required
@teacher_required
def teacher_change_password(request):
    """教师修改密码"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(old_password):
            messages.error(request, '旧密码错误')
            return redirect('teacher_change_password')
        
        if new_password != confirm_password:
            messages.error(request, '两次输入的密码不一致')
            return redirect('teacher_change_password')
        
        if len(new_password) < 6:
            messages.error(request, '密码至少需要6位')
            return redirect('teacher_change_password')
        
        request.user.set_password(new_password)
        request.user.save()
        
        messages.success(request, '密码修改成功！请用新密码重新登录')
        return redirect('teacher_login')
    
    return render(request, 'words/teacher/change_password.html')


# ========== 修改学生班级（新增） ==========

@login_required
@teacher_required
def update_student_class(request, student_id):
    """修改学生班级"""
    if request.method == 'POST':
        student = get_object_or_404(User, id=student_id)
        new_class = request.POST.get('new_class')
        
        if new_class:
            profile = student.userprofile
            profile.class_name = new_class
            profile.save()
            messages.success(request, f'已将 {student.first_name or student.username} 的班级修改为 {new_class}')
        else:
            messages.error(request, '请选择班级')
    
    return redirect('student_management')


# ========== 班级管理（新增） ==========

@login_required
@teacher_required
def class_management(request):
    """管理班级名称（增删改查）"""
    from django.db.models import Count
    
    # 获取所有班级及其学生数量
    classes = UserProfile.objects.filter(
        is_teacher=False,
        class_name__isnull=False
    ).exclude(
        class_name=''
    ).values('class_name').annotate(
        student_count=Count('id')
    ).order_by('class_name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'rename':
            # 重命名班级
            old_name = request.POST.get('old_name')
            new_name = request.POST.get('new_name')
            
            if old_name and new_name:
                # 批量修改该班级所有学生的班级名称
                count = UserProfile.objects.filter(
                    class_name=old_name
                ).update(class_name=new_name)
                
                # 同时修改作业中的班级名称
                Homework.objects.filter(class_name=old_name).update(class_name=new_name)
                
                messages.success(request, f'已将 "{old_name}" 重命名为 "{new_name}"，共影响 {count} 名学生')
                return redirect('class_management')
        
        elif action == 'delete':
            # 删除班级（将该班级学生设为无班级）
            class_name = request.POST.get('class_name')
            if class_name:
                count = UserProfile.objects.filter(class_name=class_name).update(class_name='')
                messages.success(request, f'已解散班级 "{class_name}"，{count} 名学生已移出')
                return redirect('class_management')
        
        elif action == 'create':
            # 创建新班级
            new_class = request.POST.get('new_class')
            if new_class:
                messages.success(request, f'班级 "{new_class}" 已创建（有学生选择此班级后生效）')
                return redirect('class_management')
    
    return render(request, 'words/teacher/class_management.html', {
        'classes': classes
    })
# ========== 单词编辑与删除（新增） ==========

@login_required
@teacher_required
def edit_word(request, word_id):
    """编辑单词"""
    word = get_object_or_404(Word, id=word_id)
    
    if request.method == 'POST':
        word.word = request.POST.get('word')
        word.pronunciation = request.POST.get('pronunciation', '')
        word.definition = request.POST.get('definition')
        word.example = request.POST.get('example', '')
        word.example_translation = request.POST.get('example_translation', '')
        word.difficulty = int(request.POST.get('difficulty', 3))
        word.category = request.POST.get('category', '')
        word.save()
        messages.success(request, f'单词 "{word.word}" 更新成功')
        return redirect('word_management')
    
    return render(request, 'words/teacher/edit_word.html', {'word': word})

@login_required
@teacher_required
def delete_word(request, word_id):
    """删除单词"""
    word = get_object_or_404(Word, id=word_id)
    word_name = word.word
    word.delete()
    messages.success(request, f'单词 "{word_name}" 已删除')
    return redirect('word_management')
