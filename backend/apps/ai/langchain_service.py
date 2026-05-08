"""
LangChain 服务层 — 封装 6 条工作流的调用逻辑。
提供与原有 services.py 兼容的接口，视图层改动最小化。
"""

import logging
from typing import Iterator

from langchain_core.runnables import RunnableSerializable

from apps.ai.chains import (
    build_destination_analysis_chain,
    build_post_polish_chain,
    build_post_summary_chain,
    build_scenic_qa_chain,
    build_travel_assistant_chain,
    build_trip_planner_chain,
)

logger = logging.getLogger("apps.ai")


class LangChainServiceError(Exception):
    pass


def _invoke_chain(chain: RunnableSerializable, params: dict) -> str:
    """同步调用链，返回完整结果。"""
    try:
        result = chain.invoke(params)
        return str(result).strip()
    except Exception as exc:
        logger.error("LangChain invoke failed: %s", exc, exc_info=True)
        raise LangChainServiceError(f"AI 服务调用失败：{exc}") from exc


def _stream_chain(chain: RunnableSerializable, params: dict) -> Iterator[str]:
    """流式调用链，逐块返回文本。"""
    try:
        for chunk in chain.stream(params):
            yield str(chunk)
    except Exception as exc:
        logger.error("LangChain stream failed: %s", exc, exc_info=True)
        raise LangChainServiceError(f"AI 服务流式调用失败：{exc}") from exc


# ═══════════════════════════════════════════════
# 工作流 1：景点智能问答
# ═══════════════════════════════════════════════

def scenic_qa(provider: str, context: str, question: str, model: str | None = None) -> str:
    """基于景点资料回答用户问题。「景点智能问答」"""
    chain = build_scenic_qa_chain(provider, model)
    return _invoke_chain(chain, {"context": context, "question": question})


def scenic_qa_stream(provider: str, context: str, question: str, model: str | None = None) -> Iterator[str]:
    """流式版本。「景点智能问答（流式）」"""
    chain = build_scenic_qa_chain(provider, model)
    return _stream_chain(chain, {"context": context, "question": question})


# ═══════════════════════════════════════════════
# 工作流 2：旅行助手
# ═══════════════════════════════════════════════

def travel_assistant(
    provider: str,
    departure_city: str,
    destination_city: str,
    days: str,
    budget: str,
    preferences: str,
    draft_itinerary: str = "",
    model: str | None = None,
) -> str:
    """根据旅行需求生成建议。「旅行助手」"""
    chain = build_travel_assistant_chain(provider, model)
    return _invoke_chain(chain, {
        "departure_city": departure_city,
        "destination_city": destination_city,
        "days": days,
        "budget": budget,
        "preferences": preferences,
        "draft_itinerary": draft_itinerary,
    })


def travel_assistant_stream(
    provider: str,
    departure_city: str,
    destination_city: str,
    days: str,
    budget: str,
    preferences: str,
    draft_itinerary: str = "",
    model: str | None = None,
) -> Iterator[str]:
    """流式版本。「旅行助手（流式）」"""
    chain = build_travel_assistant_chain(provider, model)
    return _stream_chain(chain, {
        "departure_city": departure_city,
        "destination_city": destination_city,
        "days": days,
        "budget": budget,
        "preferences": preferences,
        "draft_itinerary": draft_itinerary,
    })


# ═══════════════════════════════════════════════
# 工作流 3：景点数据分析
# ═══════════════════════════════════════════════

def destination_analysis(provider: str, context: str, model: str | None = None) -> str:
    """分析景点评分和评价。「景点数据分析」"""
    chain = build_destination_analysis_chain(provider, model)
    return _invoke_chain(chain, {"context": context})


def destination_analysis_stream(provider: str, context: str, model: str | None = None) -> Iterator[str]:
    """流式版本。「景点数据分析（流式）」"""
    chain = build_destination_analysis_chain(provider, model)
    return _stream_chain(chain, {"context": context})


# ═══════════════════════════════════════════════
# 工作流 4：景点规划
# ═══════════════════════════════════════════════

def trip_planner(
    provider: str,
    destination_city: str,
    days: int,
    budget: int,
    preferences: str,
    candidates: str,
    model: str | None = None,
) -> str:
    """根据候选景点生成行程规划。「景点规划」"""
    chain = build_trip_planner_chain(provider, model)
    return _invoke_chain(chain, {
        "destination_city": destination_city,
        "days": str(days),
        "budget": str(budget),
        "preferences": preferences,
        "candidates": candidates,
    })


def trip_planner_stream(
    provider: str,
    destination_city: str,
    days: int,
    budget: int,
    preferences: str,
    candidates: str,
    model: str | None = None,
) -> Iterator[str]:
    """流式版本。「景点规划（流式）」"""
    chain = build_trip_planner_chain(provider, model)
    return _stream_chain(chain, {
        "destination_city": destination_city,
        "days": str(days),
        "budget": str(budget),
        "preferences": preferences,
        "candidates": candidates,
    })


# ═══════════════════════════════════════════════
# 工作流 5：内容润色
# ═══════════════════════════════════════════════

def post_polish(provider: str, title: str, content: str, tags: str, model: str | None = None) -> str:
    """润色帖子标题和正文。「内容润色」"""
    chain = build_post_polish_chain(provider, model)
    return _invoke_chain(chain, {"title": title, "content": content, "tags": tags})


def post_polish_stream(provider: str, title: str, content: str, tags: str, model: str | None = None) -> Iterator[str]:
    """流式版本。「内容润色（流式）」"""
    chain = build_post_polish_chain(provider, model)
    return _stream_chain(chain, {"title": title, "content": content, "tags": tags})


# ═══════════════════════════════════════════════
# 工作流 6：帖子总结
# ═══════════════════════════════════════════════

def post_summary(
    provider: str,
    title: str,
    destination_name: str,
    content: str,
    tags: str,
    comments_summary: str,
    model: str | None = None,
) -> str:
    """总结帖子内容与评论。「帖子总结」"""
    chain = build_post_summary_chain(provider, model)
    return _invoke_chain(chain, {
        "title": title,
        "destination_name": destination_name,
        "content": content,
        "tags": tags,
        "comments_summary": comments_summary,
    })


def post_summary_stream(
    provider: str,
    title: str,
    destination_name: str,
    content: str,
    tags: str,
    comments_summary: str,
    model: str | None = None,
) -> Iterator[str]:
    """流式版本。「帖子总结（流式）」"""
    chain = build_post_summary_chain(provider, model)
    return _stream_chain(chain, {
        "title": title,
        "destination_name": destination_name,
        "content": content,
        "tags": tags,
        "comments_summary": comments_summary,
    })


# ═══════════════════════════════════════════════
# 工作流 7：智能搜索
# ═══════════════════════════════════════════════

from apps.ai.chains import build_smart_search_chain


def smart_search(provider: str, keyword: str, candidates: str, model: str | None = None) -> str:
    """根据搜索词和候选景点生成搜索建议。「智能搜索」"""
    chain = build_smart_search_chain(provider, model)
    return _invoke_chain(chain, {"keyword": keyword, "candidates": candidates})


def smart_search_stream(provider: str, keyword: str, candidates: str, model: str | None = None) -> Iterator[str]:
    """流式版本。「智能搜索（流式）」"""
    chain = build_smart_search_chain(provider, model)
    return _stream_chain(chain, {"keyword": keyword, "candidates": candidates})
