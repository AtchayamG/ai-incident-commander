from app.security.redaction import redact


def test_openai_key_redacted() -> None:
    result = redact("config: api uses sk-demo1234567890abcdef for auth")
    assert "sk-demo1234567890abcdef" not in result.content
    assert result.applied
    assert "openai_key" in result.matched_rules


def test_assigned_secret_redacted_but_key_name_kept() -> None:
    result = redact("api_key=super-secret-value retries=3")
    assert "super-secret-value" not in result.content
    assert "api_key=" in result.content
    assert result.applied


def test_aws_and_github_tokens_redacted() -> None:
    result = redact("AKIAIOSFODNN7EXAMPLE and ghp_abcdefghijklmnopqrstuv123456")
    assert "AKIAIOSFODNN7EXAMPLE" not in result.content
    assert "ghp_abcdefghijklmnopqrstuv123456" not in result.content
    assert {"aws_access_key", "github_token"} <= set(result.matched_rules)


def test_url_credentials_redacted_scheme_kept() -> None:
    result = redact("db url postgres://admin:hunter2@db.internal:5432/app")
    assert "hunter2" not in result.content
    assert "postgres://" in result.content


def test_email_redacted() -> None:
    result = redact("reported by oncall@example.com")
    assert "oncall@example.com" not in result.content


def test_private_key_block_redacted() -> None:
    block = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----"
    result = redact(f"leaked: {block}")
    assert "MIIEow" not in result.content


def test_benign_text_untouched() -> None:
    text = "ERROR TypeError at payments/charge.py:42 in apply_discount"
    result = redact(text)
    assert result.content == text
    assert not result.applied
    assert result.matched_rules == []
