from __future__ import annotations

import re

import requests

from ..config import settings


def mask_phone(content: str) -> str:
    return re.sub(r"(?<!\d)(1[3-9]\d{2})\d{4}(\d{4})(?!\d)", r"\1****\2", content)


class WeComBot:
    def __init__(self) -> None:
        self.webhook_url = settings.wecom_webhook_url

    def send_markdown(self, content: str) -> bool:
        """
        如果 WECOM_WEBHOOK_URL 存在，则 POST 到企业微信群机器人 webhook。
        如果不存在，则 print 到控制台，并返回 True。
        """
        content = mask_phone(content)
        if not self.webhook_url:
            print(f"[WeComBot:markdown]\n{content}")
            return True
        response = requests.post(
            self.webhook_url,
            json={"msgtype": "markdown", "markdown": {"content": content}},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("errcode", 0) == 0

    def send_text(self, content: str) -> bool:
        """
        发送文本消息。
        """
        content = mask_phone(content)
        if not self.webhook_url:
            print(f"[WeComBot:text]\n{content}")
            return True
        response = requests.post(
            self.webhook_url,
            json={"msgtype": "text", "text": {"content": content}},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("errcode", 0) == 0
