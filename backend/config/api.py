"""
自定义 DRF 渲染器 — 将非流式 JSON 响应统一包装为:
{status_code, data, message} 标准信封格式。
"""

from collections.abc import Mapping

from rest_framework.renderers import JSONRenderer


def _first_message(data):
    """从响应数据中递归提取第一条 message/detail/non_field_errors 文本。"""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return _first_message(data[0]) if data else ""
    if isinstance(data, Mapping):
        for key in ("message", "detail", "non_field_errors"):
            if key in data:
                return _first_message(data[key])
        for value in data.values():
            message = _first_message(value)
            if message:
                return message
    return ""


class StandardJSONRenderer(JSONRenderer):
    """
    Render every non-streaming DRF JSON response as:
    {
      "status_code": 200,
      "data": ...,
      "message": "..."
    }
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        status_code = getattr(response, "status_code", 200)

        if isinstance(data, Mapping) and {"status_code", "data", "message"}.issubset(data.keys()):
            envelope = data
        else:
            message = _first_message(data)
            if not message:
                message = "请求成功" if status_code < 400 else "请求失败"
            envelope = {
                "status_code": status_code,
                "data": data,
                "message": message,
            }

        return super().render(envelope, accepted_media_type, renderer_context)
