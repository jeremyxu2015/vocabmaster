from django.core.management.base import BaseCommand
from words.models import Word

class Command(BaseCommand):
    help = 'Import sample words'

    def handle(self, *args, **kwargs):
        sample_words = [
            {
                "word": "serendipity",
                "pronunciation": "ˌserənˈdɪpəti",
                "definition": "n. 意外发现珍奇事物的本领；机缘凑巧",
                "example": "Meeting her was pure serendipity.",
                "example_translation": "遇见她纯属机缘巧合。",
                "category": "advanced"
            },
            {
                "word": "ephemeral",
                "pronunciation": "ɪˈfemərəl",
                "definition": "adj. 短暂的；朝生暮死的",
                "example": "Fashion is ephemeral, changing with every season.",
                "example_translation": "时尚是短暂的，每季都在变化。",
                "category": "advanced"
            },
            {
                "word": "resilience",
                "pronunciation": "rɪˈzɪliəns",
                "definition": "n. 恢复力；弹力；顺应力",
                "example": "She showed great resilience in the face of adversity.",
                "example_translation": "她在逆境中表现出了极大的韧性。",
                "category": "intermediate"
            },
            {
                "word": "ambiguous",
                "pronunciation": "æmˈbɪɡjuəs",
                "definition": "adj. 模棱两可的；含糊不清的",
                "example": "The contract is ambiguous in this section.",
                "example_translation": "合同的这一部分表述含糊。",
                "category": "intermediate"
            },
            {
                "word": "pragmatic",
                "pronunciation": "præɡˈmætɪk",
                "definition": "adj. 实用的；务实的",
                "example": "We need a pragmatic solution to this problem.",
                "example_translation": "我们需要一个务实的解决方案。",
                "category": "intermediate"
            }
        ]
        
        count = 0
        for item in sample_words:
            word, created = Word.objects.get_or_create(
                word=item['word'],
                defaults=item
            )
            if created:
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'成功导入 {count} 个新单词，共 {len(sample_words)} 个检查完毕'))
