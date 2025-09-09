import yagmail, os, json

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
MOD_EMAIL = os.getenv("RECIPIENT_EMAIL")

def notify_human(subject: str, message: str, context: dict = None):
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)
        body = message
        if context:
            body += "\n\nContext:\n" + json.dumps(context, indent=2)
        yag.send(to=MOD_EMAIL, subject=subject, contents=body)
    except Exception as e:
        print(f"Failed to notify human: {e}")
