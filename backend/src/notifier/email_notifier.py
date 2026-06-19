import logging
from datetime import date
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from ..auth import gen_feedback_token
from ..config import BASE_URL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
from ..models import User, Paper
from .base import BaseNotifier

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


class EmailNotifier(BaseNotifier):
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )

    async def send_digest(self, user: User, papers: list[Paper], digest_date: date) -> bool:
        if not user.notify_email or not user.email:
            logger.info("Skipping email: user %s has no email or notify disabled", user.username)
            return False

        if not SMTP_HOST:
            logger.warning("Skipping email: SMTP_HOST not configured")
            return False

        if not papers:
            logger.info("Skipping email: no papers to send")
            return False

        paper_data = []
        for paper in papers:
            summary = paper.summary_cn or {}
            venue_display = ""
            if paper.venue:
                venue_display = f"{paper.venue}（已见刊）"
            elif paper.venue_hint:
                venue_display = f"{paper.venue_hint}（录用指向）"

            paper_data.append({
                "id": paper.id,
                "title": paper.title,
                "title_cn": summary.get("title_cn", ""),
                "abstract_cn": summary.get("abstract_cn", ""),
                "summary_cn": summary.get("summary_cn", ""),
                "venue_display": venue_display,
                "pdf_url": paper.pdf_url or "",
                "tokens": {
                    "interested": gen_feedback_token(paper.id, "interested"),
                    "not_interested": gen_feedback_token(paper.id, "not_interested"),
                    "read_later": gen_feedback_token(paper.id, "read_later"),
                },
            })

        template = self._env.get_template("email.html")
        html_body = template.render(papers=paper_data, date=str(digest_date), base_url=BASE_URL)

        msg = EmailMessage()
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = user.email
        msg["Subject"] = f"Paper Digest · {digest_date}"
        msg.set_content("Paper Digest HTML email.")
        msg.add_alternative(html_body, subtype="html")

        try:
            await aiosmtplib.send(
                msg,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER or None,
                password=SMTP_PASSWORD or None,
                start_tls=True,
            )
            logger.info("Digest email sent to %s for %s (%d papers)", user.email, digest_date, len(papers))
            return True
        except Exception:
            logger.exception("Failed to send digest email to %s", user.email)
            return False
