import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr


class MailConfigError(RuntimeError):
    pass


def _get_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def send_mail(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    host = (os.getenv('SMTP_HOST') or '').strip()
    port_raw = (os.getenv('SMTP_PORT') or '').strip()
    username = (os.getenv('SMTP_USERNAME') or '').strip() or None
    password = (os.getenv('SMTP_PASSWORD') or '').strip() or None

    use_tls = _get_bool_env('SMTP_USE_TLS', True)
    use_ssl = _get_bool_env('SMTP_USE_SSL', False)

    from_email = (os.getenv('SMTP_FROM') or '').strip()
    from_name = (os.getenv('SMTP_FROM_NAME') or '').strip() or None

    if not host:
        raise MailConfigError('SMTP_HOST is not configured')
    if not port_raw:
        raise MailConfigError('SMTP_PORT is not configured')
    if not from_email:
        raise MailConfigError('SMTP_FROM is not configured')

    try:
        port = int(port_raw)
    except ValueError as e:
        raise MailConfigError('SMTP_PORT must be an integer') from e

    if use_ssl and use_tls:
        raise MailConfigError('Only one of SMTP_USE_SSL or SMTP_USE_TLS can be enabled')

    msg = EmailMessage()
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['From'] = formataddr((from_name, from_email)) if from_name else from_email

    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    if use_ssl:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host=host, port=port, timeout=20)
    else:
        server = smtplib.SMTP(host=host, port=port, timeout=20)

    try:
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        if username and password:
            server.login(username, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
