"""
AI 内容造数据脚本
用法: python manage.py seed_ai_content

在下方 SPOTS 列表中填写 省份、城市、景点名称，
运行后自动用千问大模型生成景点简介、标签，并为每个景点生成 1-2 篇 AI 旅行帖子。
"""

import os
import random
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.db import transaction

from apps.ai.services import chat_completion
from apps.travel.models import Destination

# ═══════════════════════════════════════════════
# 在这里填写要生成的景点（省份、城市、景点名）
# ═══════════════════════════════════════════════
SPOTS = [
    {"province": "四川", "city": "成都", "name": "青城山"},
    {"province": "浙江", "city": "杭州", "name": "千岛湖"},
    {"province": "云南", "city": "大理", "name": "洱海"},
]

# ═══════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════
AI_PROVIDER = "qwen"
POSTS_PER_SPOT = 2  # 每个景点生成几篇帖子
PLACEHOLDER_IMAGE = "https://picsum.photos/800/400"  # 封面占位图（千问不支持生图）


def ai_generate(prompt, system_prompt=None, temperature=0.85):
    """调用千问大模型生成文本"""
    return chat_completion(
        provider=AI_PROVIDER,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
    )


def generate_destination_info(spot):
    """AI 生成景点简介、标签、建议游玩天数、最佳季节"""
    prompt = f"""请为景点生成信息，返回 JSON 格式：
{{
  "summary": "景点简介，80-150字，生动吸引人",
  "tags": "标签1,标签2,标签3,标签4,标签5",
  "suggested_days": 建议游玩天数(1-5的整数),
  "best_season": "最佳游玩季节",
  "budget_level": "经济/中等/偏高",
  "ticket_price": 门票价格(数字)
}}

景点：{spot['province']}省{spot['city']}市 {spot['name']}"""
    
    system = "你是旅游内容专家，只返回合法的 JSON，不要有任何额外文字。"
    
    for attempt in range(3):
        try:
            raw = ai_generate(prompt, system_prompt=system, temperature=0.7)
            # 提取 JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                import json
                return json.loads(raw[start:end])
        except Exception:
            time.sleep(1)
    
    # 兜底
    return {
        "summary": f"{spot['name']}是{spot['province']}{spot['city']}的著名景点，风景秀美，文化底蕴深厚，适合休闲度假与深度游览。",
        "tags": "自然风光,人文历史,休闲度假,摄影,美食",
        "suggested_days": 2,
        "best_season": "春秋季",
        "budget_level": "中等",
        "ticket_price": 60,
    }


def generate_post(spot, post_index):
    """AI 生成一篇旅行帖子"""
    style = random.choice(["游记", "攻略", "探店", "摄影分享", "避坑指南"])
    
    prompt = f"""请以一位旅行者的口吻，写一篇关于{spot['province']}{spot['city']}{spot['name']}的{style}帖子。

要求：
1. 标题：10-25字，吸引人，有温度
2. 正文：200-400字，包含真实感细节（路线、花费、感受、小建议）
3. 标签：3-5个，用逗号分隔

返回 JSON：
{{
  "title": "帖子标题",
  "content": "帖子正文...",
  "tags": "标签1,标签2,标签3"
}}"""
    
    system = "你是热爱旅行的普通游客，写帖自然真诚，不用官方语气。只返回合法 JSON。"
    
    for attempt in range(3):
        try:
            raw = ai_generate(prompt, system_prompt=system, temperature=0.9)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                import json
                data = json.loads(raw[start:end])
                return {
                    "title": data.get("title", f"{spot['name']}{style}记"),
                    "content": data.get("content", ""),
                    "tags": data.get("tags", ""),
                }
        except Exception:
            time.sleep(1)
    
    return {
        "title": f"漫游{spot['name']} | 第{post_index}篇{style}",
        "content": f"来了{spot['city']}，{spot['name']}是必打卡的地方……",
        "tags": "旅行,分享",
    }


def get_random_user():
    """随机选一个已有用户作为帖子作者"""
    users = list(User.objects.filter(is_active=True)[:50])
    if not users:
        print("❌ 没有可用用户，请先创建账号")
        sys.exit(1)
    return random.choice(users)


def main():
    print(f"\n{'='*60}")
    print(f"  AI 内容造数据脚本")
    print(f"  模型: {AI_PROVIDER}  |  景点: {len(SPOTS)} 个  |  每景点 {POSTS_PER_SPOT} 篇帖子")
    print(f"{'='*60}\n")

    total_destinations = 0
    total_posts = 0

    for spot in SPOTS:
        print(f"📍 {spot['province']} {spot['city']} · {spot['name']}")

        # 1. 检查是否已存在
        existing = Destination.objects.filter(
            name__iexact=spot["name"],
            city__iexact=spot["city"],
            province__iexact=spot["province"],
        ).first()

        if existing:
            print(f"   ⚠️  景点已存在 (id={existing.id})，跳过创建，直接生成帖子")
            destination = existing
        else:
            # 2. AI 生成景点信息
            info = generate_destination_info(spot)
            destination = Destination.objects.create(
                name=spot["name"],
                city=spot["city"],
                province=spot["province"],
                cover=PLACEHOLDER_IMAGE,
                summary=info.get("summary", ""),
                tags=info.get("tags", ""),
                budget_level=info.get("budget_level", "中等"),
                best_season=info.get("best_season", ""),
                suggested_days=info.get("suggested_days", 2),
                ticket_price=info.get("ticket_price", 0),
                score=round(random.uniform(3.5, 5.0), 1),
            )
            total_destinations += 1
            print(f"   ✅ 景点已创建  | 简介: {info.get('summary', '')[:40]}...")

        # 3. AI 生成帖子
        from apps.social.models import Post

        author = get_random_user()
        for i in range(1, POSTS_PER_SPOT + 1):
            post_data = generate_post(spot, i)
            Post.objects.create(
                author=author,
                destination=destination,
                title=post_data["title"],
                content=post_data["content"],
                cover=PLACEHOLDER_IMAGE,
                tags=post_data["tags"],
                status="approved",  # 直接发布
            )
            total_posts += 1
            print(f"   📝 帖子 {i}/{POSTS_PER_SPOT}: 《{post_data['title']}》")

        # 限速，避免 API 频率限制
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"  ✅ 完成！")
    print(f"  新增景点: {total_destinations}  新增帖子: {total_posts}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
