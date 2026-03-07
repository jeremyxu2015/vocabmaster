import datetime
from django.utils import timezone

def calculate_next_review(user_word, quality):
    """
    SM-2 算法实现
    quality: 0-5 评分，0=完全不会, 5=完美回答
    返回：下次间隔天数
    """
    if quality < 0 or quality > 5:
        quality = 0
    
    user_word.total_reviews += 1
    user_word.last_reviewed = timezone.now()
    
    if quality >= 3:
        # 回答正确
        user_word.correct_count += 1
        
        if user_word.repetitions == 0:
            user_word.interval = 1
        elif user_word.repetitions == 1:
            user_word.interval = 6
        else:
            user_word.interval = int(user_word.interval * user_word.ease_factor)
        
        user_word.repetitions += 1
    else:
        # 回答错误，重置
        user_word.wrong_count += 1
        user_word.repetitions = 0
        user_word.interval = 1
    
    # 更新简易度系数 (EF) 公式：EF + (0.1 - (5-q)*(0.08 + (5-q)*0.02))
    user_word.ease_factor = max(1.3, user_word.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    # 计算下次复习时间
    user_word.next_review = timezone.now() + datetime.timedelta(days=user_word.interval)
    
    # 标记为已学习（至少复习过一次）
    if user_word.repetitions >= 1:
        user_word.is_learned = True
    
    user_word.save()
    return user_word.interval