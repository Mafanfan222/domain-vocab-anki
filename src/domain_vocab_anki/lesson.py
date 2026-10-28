"""Render one complete, reproducible lesson."""

from datetime import date, timedelta
import re

from .config import Profile
from .models import Word


def render(day: date, profile: Profile, payload: dict) -> str:
    words = [Word.from_dict(item) for item in payload["words"]]
    reviews = payload["reviews"]
    lines = [f"# {day.isoformat()} · {profile.name}", "", "## 1. 间隔复习", ""]
    if not reviews:
        lines.append("今日暂无到期复习。" if payload.get("has_history") else "今日为第一课，暂无间隔复习。")
    for index, review in enumerate(reviews, 1):
        word = Word.from_dict(review["word"])
        lines.append(f"{index}. 【D+{review['interval_day']}】中译英：{word.meaning_zh}（{word.context_zh}）")
    lines.extend(["", "## 2. 今日10词" if len(words) == 10 else f"## 2. 今日{len(words)}词", ""])
    for index, word in enumerate(words, 1):
        lines.extend([
            f"{index}. **{word.term}** {word.ipa} · {word.part_of_speech} · {word.meaning_zh}",
            f"   - 场景：{word.context_zh}",
            f"   - 例句：{word.example_en} / {word.example_zh}",
            f"   - 搭配/易错：{word.collocation_zh}",
        ])
    format_names = {"dialogue": "对话", "explanation": "说明", "story": "故事", "guide": "指南"}
    lines.extend(["", f"## 3. 领域英语示例（{format_names[profile.sample_format]}）", "", payload["sample_en"], "", payload["sample_zh"], "", "## 4. 应用练习", "", payload["practice_task_zh"], "", "## 5. 今日小测", ""])
    quiz = words[:3]
    for index, word in enumerate(quiz, 1):
        blank = re.sub(re.escape(word.term), "_____", word.example_en, count=1, flags=re.I)
        lines.append(f"{index}. 根据语境填入今天的词：{blank}")
    lines.extend(["", "## 6. 答案与简析", ""])
    for index, review in enumerate(reviews, 1):
        word = Word.from_dict(review["word"])
        lines.append(f"- 复习 {index}：**{word.term}**。{word.collocation_zh}")
    for index, word in enumerate(quiz, 1):
        lines.append(f"- 小测 {index}：**{word.term}**。{word.meaning_zh}；{word.collocation_zh}")
    next_review = day + timedelta(days=profile.review_intervals[0])
    lines.extend([
        "", "## 7. 学习记录", "",
        f"新增（首次学习 {day.isoformat()}；复习次数 0；掌握状态：待评估）：{', '.join(word.term for word in words)}。",
        f"今日复习：{', '.join('D+' + str(item['interval_day']) for item in reviews) or '无'}（未收到答题结果，不判定正误）；新词下次计划复习：{next_review.isoformat()}。",
        "回复复习题答案，或使用 `grade` 命令记录结果以调整计划。",
        "",
    ])
    return "\n".join(lines)
