from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from unittest.mock import patch, MagicMock

from mcp_notmuch_sendmail.notmuchlib import (
    fmt_timestamp,
    normalize_empty_lines,
    extract_reply,
    decode_qp,
    format_attachment_size,
    save_attachments,
    get_attachments_summary,
    get_message_attachments,
    extract_thread_attachments,
    message_to_text,
)


def test_fmt_timestamp_formats_date():
    assert fmt_timestamp(1706140800) == "2024-01-25"


def test_normalize_empty_lines_collapses_blanks():
    assert normalize_empty_lines("a\n\n\n\nb") == "a\n\nb"


def test_normalize_empty_lines_preserves_single_blank():
    assert normalize_empty_lines("a\n\nb") == "a\n\nb"


def test_extract_reply_trims_at_separator():
    text = "Hello there\nOn Monday someone wrote:\nquoted stuff"
    assert extract_reply(text) == "Hello there"


def test_extract_reply_returns_full_text_without_separator():
    text = "Hello there\nNo separator here"
    assert extract_reply(text) == "Hello there\nNo separator here"


def test_extract_reply_case_insensitive():
    text = "Hello\nfrom: someone"
    assert extract_reply(text) == "Hello"


def test_decode_qp_utf8():
    encoded = "=C3=A9"
    assert decode_qp(encoded) == "\u00e9"


def test_decode_qp_latin1_fallback():
    encoded = "=E9"
    assert decode_qp(encoded) == "\u00e9"


def test_format_attachment_size_bytes():
    assert format_attachment_size(500) == "500 B"


def test_format_attachment_size_kilobytes():
    assert format_attachment_size(46284) == "45.2 KB"


def test_format_attachment_size_megabytes():
    assert format_attachment_size(5242880) == "5.0 MB"


def test_save_attachments_writes_files(tmp_path):
    attachments = [("report.pdf", b"pdf content"), ("image.png", b"png content")]
    result = save_attachments(attachments, tmp_path)
    assert (tmp_path / "1_report.pdf").read_bytes() == b"pdf content"
    assert (tmp_path / "2_image.png").read_bytes() == b"png content"
    assert len(result) == 2
    assert result[0]["filename"] == "1_report.pdf"
    assert result[1]["filename"] == "2_image.png"


def test_save_attachments_counter_handles_collisions(tmp_path):
    attachments = [("file.txt", b"aaa"), ("file.txt", b"bbb")]
    result = save_attachments(attachments, tmp_path)
    assert (tmp_path / "1_file.txt").read_bytes() == b"aaa"
    assert (tmp_path / "2_file.txt").read_bytes() == b"bbb"


def test_save_attachments_returns_metadata(tmp_path):
    attachments = [("doc.pdf", b"x" * 1024)]
    result = save_attachments(attachments, tmp_path)
    assert result[0]["size"] == 1024
    assert result[0]["path"] == str(tmp_path / "1_doc.pdf")


def _make_mime_message(parts):
    """Helper to build a MIME message with given parts for testing."""
    msg = MIMEMultipart()
    for part in parts:
        msg.attach(part)
    return msg


def test_get_attachments_summary_finds_attachment_with_filename():
    text_part = MIMEText("hello", "html")
    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(b"x" * 2048)
    attachment.add_header("Content-Disposition", "attachment", filename="report.pdf")
    msg = _make_mime_message([text_part, attachment])

    result = get_attachments_summary(msg)
    assert len(result) == 1
    assert result[0]["filename"] == "report.pdf"
    assert result[0]["size"] == 2048
    assert result[0]["content_type"] == "application/pdf"


def test_get_attachments_summary_skips_text_without_disposition():
    text_part = MIMEText("hello", "html")
    plain_part = MIMEText("plain version", "plain")
    msg = _make_mime_message([text_part, plain_part])

    result = get_attachments_summary(msg)
    assert result == []


def test_get_attachments_summary_includes_disposition_attachment_without_filename():
    part = MIMEBase("application", "octet-stream")
    part.set_payload(b"data")
    part.add_header("Content-Disposition", "attachment")
    msg = _make_mime_message([part])

    result = get_attachments_summary(msg)
    assert len(result) == 1
    assert result[0]["filename"] is None


class FakeNotmuchMessage:
    """Mimics the notmuch message interface used by message_to_text."""

    def __init__(self, headers, date, parts):
        self._headers = headers
        self._date = date
        self._parts = parts

    def get_header(self, name):
        return self._headers.get(name, "")

    def get_date(self):
        return self._date

    def get_message_parts(self):
        return self._parts


def test_message_to_text_includes_attachment_summary():
    html_part = MIMEText("<p>Hello</p>", "html")
    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(b"x" * 2048)
    attachment.add_header("Content-Disposition", "attachment", filename="report.pdf")

    msg = FakeNotmuchMessage(
        headers={"From": "alice@example.com"},
        date=1706140800,
        parts=[html_part, attachment],
    )
    text = message_to_text(msg)
    assert "ATTACHMENTS:" in text
    assert "report.pdf" in text
    assert "2.0 KB" in text


def test_message_to_text_no_attachments_no_section():
    html_part = MIMEText("<p>Hello</p>", "html")

    msg = FakeNotmuchMessage(
        headers={"From": "alice@example.com"},
        date=1706140800,
        parts=[html_part],
    )
    text = message_to_text(msg)
    assert "ATTACHMENTS:" not in text


def test_get_message_attachments_extracts_data():
    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(b"pdf data")
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename="report.pdf")

    msg = FakeNotmuchMessage(
        headers={"From": "alice@example.com"},
        date=1706140800,
        parts=[MIMEText("hello", "html"), attachment],
    )
    result = get_message_attachments(msg)
    assert len(result) == 1
    assert result[0][0] == "report.pdf"
    assert result[0][1] == b"pdf data"


def test_get_message_attachments_skips_text_parts():
    msg = FakeNotmuchMessage(
        headers={"From": "alice@example.com"},
        date=1706140800,
        parts=[MIMEText("hello", "html"), MIMEText("plain", "plain")],
    )
    result = get_message_attachments(msg)
    assert result == []


def test_get_message_attachments_fallback_filename():
    part = MIMEBase("application", "octet-stream")
    part.set_payload(b"data")
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment")

    msg = FakeNotmuchMessage(
        headers={"From": "alice@example.com"},
        date=1706140800,
        parts=[part],
    )
    result = get_message_attachments(msg)
    assert len(result) == 1
    assert result[0][0] == "attachment_1"


def test_extract_thread_attachments_saves_to_dir(tmp_path):
    att1 = MIMEBase("application", "pdf")
    att1.set_payload(b"pdf1")
    encoders.encode_base64(att1)
    att1.add_header("Content-Disposition", "attachment", filename="doc.pdf")

    att2 = MIMEBase("image", "png")
    att2.set_payload(b"png1")
    encoders.encode_base64(att2)
    att2.add_header("Content-Disposition", "attachment", filename="pic.png")

    msg1 = FakeNotmuchMessage(
        headers={"From": "alice@example.com"}, date=1706140800,
        parts=[MIMEText("hi", "html"), att1],
    )
    msg2 = FakeNotmuchMessage(
        headers={"From": "bob@example.com"}, date=1706140900,
        parts=[MIMEText("reply", "html"), att2],
    )

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.search_messages.return_value = iter([msg1, msg2])

    with patch("mcp_notmuch_sendmail.notmuchlib.Database", return_value=mock_db), \
         patch("mcp_notmuch_sendmail.notmuchlib.Query", return_value=mock_query), \
         patch("mcp_notmuch_sendmail.notmuchlib.DRAFT_DIR", tmp_path):
        result = extract_thread_attachments("thread123")

    dest = tmp_path / "attachments" / "thread123"
    assert dest.exists()
    assert (dest / "1_doc.pdf").read_bytes() == b"pdf1"
    assert (dest / "2_pic.png").read_bytes() == b"png1"
    assert "doc.pdf" in result
    assert "pic.png" in result
