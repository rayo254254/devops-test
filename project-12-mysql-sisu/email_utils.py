import smtplib
import mimetypes
from email.message import EmailMessage
from email.utils import formataddr


def send_email(
    subject,
    body,
    sender_email,
    sender_name,
    sender_password,
    recipient_email,
    recipient_cc=None,
    recipient_bcc=None,
    reply_to=None,
    attachment_bytes=None,
    attachment_filename=None,
    smtp_server="smtp.gmail.com",
    smtp_port=587,
):
    """
    Sends an email with optional in-memory file attachment, CC, BCC, and reply-to.

    Parameters:
    - subject (str): Email subject line
    - body (str): Email body text
    - sender_email (str): Sender's email address
    - sender_password (str): Sender's app password (for Gmail)
    - recipient_email (str or list): To recipient(s)
    - recipient_cc (str or list, optional): CC recipient(s)
    - recipient_bcc (str or list, optional): BCC recipient(s)
    - reply_to (str, optional): Reply-to address
    - attachment_bytes (bytes, optional): File content as bytes
    - attachment_filename (str, optional): Filename to use for attachment
    - smtp_server (str): SMTP server address
    - smtp_port (int): SMTP port number
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = (
        formataddr((sender_name, sender_email)) if sender_name else sender_email
    )

    # Normalize addresses
    to_list = (
        [str(e) for e in recipient_email]
        if isinstance(recipient_email, list)
        else [str(recipient_email)]
    )
    cc_list = (
        [str(e) for e in recipient_cc]
        if isinstance(recipient_cc, list)
        else ([str(recipient_cc)] if recipient_cc else [])
    )
    bcc_list = (
        [str(e) for e in recipient_bcc]
        if isinstance(recipient_bcc, list)
        else ([str(recipient_bcc)] if recipient_bcc else [])
    )

    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(body)

    if attachment_bytes and attachment_filename:
        mime_type, _ = mimetypes.guess_type(attachment_filename)
        maintype, subtype = (mime_type or "application/octet-stream").split("/")
        msg.add_attachment(
            attachment_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_filename,
        )
        print(f"📎 Attached in-memory file: {attachment_filename}")

    # Combine all recipients for sending
    all_recipients = to_list + cc_list + bcc_list

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg, to_addrs=all_recipients)
            print("✅ Email sent successfully.")
            return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your email/app password.")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return False


def send_email_old(
    subject,
    body,
    sender_email,
    sender_password,
    recipient_email,
    recipient_cc=None,
    attachment_bytes=None,
    attachment_filename=None,
    smtp_server="smtp.gmail.com",
    smtp_port=587,
):
    """
    Sends an email with optional in-memory file attachment.

    Parameters:
    - subject (str): Email subject line
    - body (str): Email body text
    - sender_email (str): Sender's email address
    - sender_password (str): Sender's app password (for Gmail)
    - recipient_email (str): Recipient's email address
    - attachment_bytes (bytes, optional): File content as bytes
    - attachment_filename (str, optional): Filename to use for attachment
    - smtp_server (str): SMTP server address
    - smtp_port (int): SMTP port number
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Cc"] = recipient_cc
    msg.set_content(body)

    if attachment_bytes and attachment_filename:
        # Guess MIME type based on filename
        mime_type, _ = mimetypes.guess_type(attachment_filename)
        maintype, subtype = (mime_type or "application/octet-stream").split("/")

        msg.add_attachment(
            attachment_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_filename,
        )
        print(f"📎 Attached in-memory file: {attachment_filename}")

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("✅ Email sent successfully.")
            return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your email/app password.")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return False
