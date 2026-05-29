from mcp_notmuch_sendmail.notmuchlib import (
    fmt_timestamp,
    normalize_empty_lines,
    extract_reply,
    decode_qp,
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
