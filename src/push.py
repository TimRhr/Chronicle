import json
from typing import Any

from flask import current_app
from pywebpush import webpush, WebPushException

from extensions import db
from models import PushSubscription


def _get_vapid_claims() -> dict[str, str]:
    subject = current_app.config.get("VAPID_SUBJECT") or "mailto:admin@example.com"
    return {"sub": subject}


def send_push_notification(user_id: int, payload: dict[str, Any]) -> None:
    """Send a push notification payload to all subscriptions of a user."""
    vapid_private = current_app.config.get("VAPID_PRIVATE_KEY")
    vapid_public = current_app.config.get("VAPID_PUBLIC_KEY")
    if not vapid_private or not vapid_public:
        return

    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions:
        return

    data = json.dumps(payload)
    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=data,
                vapid_private_key=vapid_private,
                vapid_claims=_get_vapid_claims(),
            )
        except WebPushException as exc:  # pragma: no cover - network
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                db.session.delete(sub)
                db.session.commit()
        except Exception:  # pragma: no cover
            current_app.logger.exception("Error sending push notification")
