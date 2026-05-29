import os

os.environ.setdefault("NOTMUCH_DATABASE_PATH", "/tmp/test-notmuch-db")
os.environ.setdefault("NOTMUCH_REPLY_SEPARATORS", "on|wrote:|from:|sent:")
os.environ.setdefault("SENDMAIL_FROM_EMAIL", "test@example.com")
