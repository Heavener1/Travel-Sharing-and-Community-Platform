"""
LangChain 工作流定义 — 6 条 LCEL 链，替代原有裸 API 调用。

工作流清单：
1. scenic_qa_chain          — 景点智能问答（基于景点资料 RAG）
2. travel_assistant_chain   — 旅行助手（行程建议生成）
3. destination_analysis_chain — 景点数据分析（评分+评价解读）
4. trip_planner_chain       — 景点规划（根据候选景点生成行程）
5. post_polish_chain        — 内容润色（帖子标题+正文润色）
6. post_summary_chain       — 帖子总结（帖子+评论摘要）
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from django.conf import settings


# ──────────────────────────────────────────────
# 模型工厂
# ──────────────────────────────────────────────

def _create_llm(provider: str = "qwen", model: str | None = None, temperature: float = 0.7) -> ChatOpenAI:
    """创建 LangChain ChatOpenAI 实例，兼容 Kimi / 千问。"""
    provider_config = {
        "qwen": {
            "base_url": settings.QWEN_BASE_URL.replace("/chat/completions", ""),
            "api_key": settings.QWEN_API_KEY,
            "default_model": settings.QWEN_MODEL,
        },
        "kimi": {
            "base_url": settings.KIMI_BASE_URL.replace("/chat/completions", ""),
            "api_key": settings.KIMI_API_KEY,
            "default_model": settings.KIMI_MODEL,
        },
    }
    if provider not in provider_config:
        provider = "qwen"
    config = provider_config[provider]
    return ChatOpenAI(
        model=model or config["default_model"],
        openai_api_key=config["api_key"],
        openai_api_base=config["base_url"],
        temperature=temperature,
        streaming=True,
    )


# ──────────────────────────────────────────────
# 1. 景点智能问答链
# ──────────────────────────────────────────────

SCENIC_QA_SYSTEM = """你是旅游平台的景点问答助手。
请严格基于下方「景点资料」回答用户问题。
如果资料里没有明确写到，就说"根据当前系统资料暂时无法确认"，再给出保守建议。
回答请使用中文，内容清晰、实用，适合旅游场景。"""

SCENIC_QA_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(SCENIC_QA_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "景点资料：\n{context}\n\n用户问题：{question}"
    ),
])


def build_scenic_qa_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return SCENIC_QA_PROMPT | _create_llm(provider, model, temperature=0.5) | StrOutputParser()


# ──────────────────────────────────────────────
# 2. 旅行助手链
# ──────────────────────────────────────────────

TRAVEL_ASSISTANT_SYSTEM = """你是旅游分享平台的智能旅行顾问。
请基于用户提供的旅行需求，生成一份适合前端展示的旅行建议。
输出 3 个部分：1. 总体路线建议 2. 每日重点安排 3. 预算与避坑提醒。
使用中文，内容专业、可执行。"""

TRAVEL_ASSISTANT_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(TRAVEL_ASSISTANT_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "出发地：{departure_city}\n"
        "目的地：{destination_city}\n"
        "天数：{days}\n"
        "预算：{budget}\n"
        "偏好：{preferences}\n"
        "当前行程草案：{draft_itinerary}\n"
    ),
])


def build_travel_assistant_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return TRAVEL_ASSISTANT_PROMPT | _create_llm(provider, model, temperature=0.6) | StrOutputParser()


# ──────────────────────────────────────────────
# 3. 景点数据分析链
# ──────────────────────────────────────────────

DESTINATION_ANALYSIS_SYSTEM = """你是旅游平台的数据分析助手。
请基于景点资料、评分统计和用户评价，对当前景点做一份适合前端展示的分析。
输出 4 个部分：1. 景点整体印象 2. 用户评分解读 3. 优势与短板 4. 适合人群与建议。
请用中文回答，避免编造资料中没有的信息。"""

DESTINATION_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(DESTINATION_ANALYSIS_SYSTEM),
    HumanMessagePromptTemplate.from_template("{context}"),
])


def build_destination_analysis_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return DESTINATION_ANALYSIS_PROMPT | _create_llm(provider, model, temperature=0.4) | StrOutputParser()


# ──────────────────────────────────────────────
# 4. 景点规划链
# ──────────────────────────────────────────────

TRIP_PLANNER_SYSTEM = """你是旅游平台的智能行程规划师。
请根据下方候选景点列表和用户偏好，生成一份 {days} 天的个性化行程方案。
输出格式：
第1天：景点名称 — 游玩建议
第2天：景点名称 — 游玩建议
...
最后附上「总体建议」（交通、美食、注意事项各一条）。
使用中文，每条建议简洁实用，适合手机端阅读。"""

TRIP_PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(TRIP_PLANNER_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "目的地城市：{destination_city}\n"
        "出行天数：{days}\n"
        "预算：{budget} 元\n"
        "偏好：{preferences}\n"
        "候选景点：\n{candidates}\n"
    ),
])


def build_trip_planner_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return TRIP_PLANNER_PROMPT | _create_llm(provider, model, temperature=0.7) | StrOutputParser()


# ──────────────────────────────────────────────
# 5. 内容润色链
# ──────────────────────────────────────────────

POST_POLISH_SYSTEM = """你是旅游社区的内容编辑。
请将以下帖子润色为更适合发布的版本。
要求：保留真实感，不夸张，不编造没有提供的信息。
按如下格式输出：
标题：...
正文：...
标签建议：..."""

POST_POLISH_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(POST_POLISH_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "原标题：{title}\n原正文：{content}\n原标签：{tags}\n"
    ),
])


def build_post_polish_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return POST_POLISH_PROMPT | _create_llm(provider, model, temperature=0.8) | StrOutputParser()


# ──────────────────────────────────────────────
# 6. 帖子总结链
# ──────────────────────────────────────────────

POST_SUMMARY_SYSTEM = """你是旅游社区的内容总结助手。
请基于帖子正文和评论，生成适合前端展示的中文总结。
输出 3 个部分：1. 帖子核心内容 2. 评论关注点 3. 给读者的快速建议。
使用 Markdown，简洁清晰，不要编造帖子里没有的信息。"""

POST_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(POST_SUMMARY_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "帖子标题：{title}\n"
        "关联景点：{destination_name}\n"
        "帖子正文：{content}\n"
        "帖子标签：{tags}\n"
        "评论摘要：{comments_summary}\n"
    ),
])


def build_post_summary_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return POST_SUMMARY_PROMPT | _create_llm(provider, model, temperature=0.5) | StrOutputParser()


# ──────────────────────────────────────────────
# 7. 智能搜索链
# ──────────────────────────────────────────────

SMART_SEARCH_SYSTEM = """你是旅游平台的智能搜索助手。
请根据用户搜索词和候选景点，生成一段适合前端实时展示的中文搜索建议。
输出结构按以下顺序自然组织：1. 一句话总结 2. 推荐优先看的景点 3. 玩法建议 4. 适合人群。
不要编造过于具体的票价、地址或营业时间。"""

SMART_SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(SMART_SEARCH_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "用户搜索词：{keyword}\n候选景点：{candidates}\n"
    ),
])


def build_smart_search_chain(provider: str = "qwen", model: str | None = None) -> RunnableSerializable:
    return SMART_SEARCH_PROMPT | _create_llm(provider, model, temperature=0.4) | StrOutputParser()
