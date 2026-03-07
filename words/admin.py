# words/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Word, UserWord, DailyStats, UserProfile, Homework, HomeworkSubmission
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# 取消默认注册，重新注册以自定义
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'first_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'date_joined']
    search_fields = ['username', 'first_name']
    list_per_page = 20
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('first_name',)}),
        ('权限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('重要日期', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )

# 自定义 Admin 站点标题
admin.site.site_header = '📚 VocabMaster 学校版'
admin.site.site_title = 'VocabMaster'
admin.site.index_title = '欢迎使用单词学习管理系统'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'real_name', 'class_name', 'student_id', 'is_teacher', 'daily_goal', 'current_streak']
    list_filter = ['is_teacher', 'class_name']
    search_fields = ['user__username', 'real_name', 'student_id', 'class_name']
    list_editable = ['daily_goal']
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user', 'real_name', 'student_id', 'class_name', 'is_teacher'),
        }),
        ('学习设置', {
            'fields': ('daily_goal', 'current_streak', 'is_deleted'),
        }),
    )

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ['word', 'pronunciation', 'textbook', 'unit', 'is_core', 'definition_preview']
    list_filter = ['textbook', 'unit', 'is_core']
    search_fields = ['word', 'definition']
    list_per_page = 20
    
    @admin.display(description='释义')
    def definition_preview(self, obj):
        if len(obj.definition) > 30:
            return obj.definition[:30] + '...'
        return obj.definition
    
    fieldsets = (
        ('单词信息', {
            'fields': (('word', 'pronunciation'), ('textbook', 'unit'), 'is_core'),
        }),
        ('释义', {
            'fields': ('definition',),
        }),
        ('例句', {
            'fields': ('example', 'example_translation'),
            'classes': ('collapse',),
        }),
    )

@admin.register(UserWord)
class UserWordAdmin(admin.ModelAdmin):
    list_display = ['user', 'word', 'status', 'next_review', 'correct_count', 'wrong_count']
    list_filter = ['status', 'next_review']
    search_fields = ['user__username', 'word__word']
    date_hierarchy = 'next_review'
    
    @admin.display(description='状态')
    def get_status(self, obj):
        colors = {
            'new': ('#f59e0b', '新学'),
            'familiar': ('#3b82f6', '熟悉'),
            'mastered': ('#10b981', '掌握'),
        }
        color, label = colors.get(obj.status, ('#666', '未知'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, label
        )

@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'words_learned', 'words_reviewed', 'homework_done']
    list_filter = ['date', 'homework_done']
    search_fields = ['user__username']
    date_hierarchy = 'date'

@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_name', 'due_date', 'is_active', 'word_count']
    list_filter = ['class_name', 'is_active', 'due_date']
    filter_horizontal = ['words']
    
    @admin.display(description='单词数')
    def word_count(self, obj):
        return obj.words.count()

@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ['homework', 'student', 'completed_words', 'score', 'submitted_at']
    list_filter = ['homework', 'submitted_at']