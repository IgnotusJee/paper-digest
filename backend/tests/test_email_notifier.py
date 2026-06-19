import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from src.models import User, Paper
from src.notifier.email_notifier import EmailNotifier


class TestEmailNotifier:
    @pytest.mark.asyncio
    async def test_send_digest_success(self):
        user = User(
            username="test",
            email="test@example.com",
            hashed_password="x",
            notify_email=True,
        )
        paper = Paper(
            id=1,
            title="Test Paper",
            title_hash="emailtest00001",
            source="arxiv",
            summary_cn={
                "title_cn": "测试论文",
                "abstract_cn": "这是一个测试摘要",
                "summary_cn": "问题：测试 方法：mock 价值：验证",
            },
            venue="OSDI",
            pdf_url="http://example.com/paper.pdf",
        )

        notifier = EmailNotifier()
        with (
            patch("src.notifier.email_notifier.aiosmtplib.send", new_callable=AsyncMock) as mock_send,
            patch("src.notifier.email_notifier.SMTP_HOST", "smtp.test.com"),
        ):
            result = await notifier.send_digest(user, [paper], date(2025, 6, 15))

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        msg = call_args[0][0]
        assert "2025-06-15" in msg["Subject"]
        assert msg["To"] == "test@example.com"
        assert msg.is_multipart() is True
        html_part = msg.get_body(preferencelist=("html",))
        assert html_part is not None
        assert html_part.get_content_subtype() == "html"
        assert "测试论文" in html_part.get_content()

    @pytest.mark.asyncio
    async def test_send_digest_no_email(self):
        user = User(
            username="test",
            email="",
            hashed_password="x",
            notify_email=True,
        )
        paper = Paper(id=1, title="T", title_hash="emailtest00002", source="arxiv")

        notifier = EmailNotifier()
        result = await notifier.send_digest(user, [paper], date(2025, 6, 15))
        assert result is False

    @pytest.mark.asyncio
    async def test_send_digest_notify_disabled(self):
        user = User(
            username="test",
            email="test@example.com",
            hashed_password="x",
            notify_email=False,
        )
        paper = Paper(id=1, title="T", title_hash="emailtest00003", source="arxiv")

        notifier = EmailNotifier()
        result = await notifier.send_digest(user, [paper], date(2025, 6, 15))
        assert result is False

    @pytest.mark.asyncio
    async def test_send_digest_empty_papers(self):
        user = User(
            username="test",
            email="test@example.com",
            hashed_password="x",
            notify_email=True,
        )

        notifier = EmailNotifier()
        result = await notifier.send_digest(user, [], date(2025, 6, 15))
        assert result is False
