"""
Static/text-scanning regression guards for deployment hygiene (A6, A7, A9).

Regression guards, not RED-tested behavior (design, "Strict TDD: which tests
are written when"): no build step runs `migrate` today, no Blob code exists,
and `.env` is already gitignored, so these are vacuously green from the
first run. No RED was manufactured for them — no temporary `vercel.json`
running `migrate`, no fake Blob import — per the design's explicit
prohibition.

Both A6 and A7 are written in their narrowed form (design, "Why A6 and A7
were narrowed"): they assert what the requirement means, not the absence of
a file, so an unrelated future file (a linter config, a Decision-5
contingency `vercel.json`) does not fail an infrastructure test.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories that may contain application/build code relevant to A6/A7.
# `config/tests` is excluded: it legitimately mentions "migrate" and Blob
# terms in prose and assertions, not in production code paths.
SCANNED_APP_DIRS = ["config", "usuarios"]
EXCLUDED_DIR_PARTS = {"tests", "__pycache__", "migrations"}


def _iter_python_files():
    for app_dir in SCANNED_APP_DIRS:
        for path in (REPO_ROOT / app_dir).rglob("*.py"):
            if EXCLUDED_DIR_PARTS & set(path.relative_to(REPO_ROOT).parts):
                continue
            yield path


def test_a6_no_build_step_or_code_runs_migrate():
    """
    Spec: Manual, developer-triggered migrations — no build step and no
    request handler runs migrations (Automatable, narrowed).
    """
    for candidate in ("vercel.json", "pyproject.toml"):
        candidate_path = REPO_ROOT / candidate
        if candidate_path.exists():
            text = candidate_path.read_text(encoding="utf-8")
            assert "migrate" not in text, (
                f"{candidate} must not run migrations automatically"
            )

    for py_file in _iter_python_files():
        text = py_file.read_text(encoding="utf-8")
        assert 'call_command("migrate"' not in text, py_file
        assert "MigrationExecutor" not in text, py_file


def test_a7_no_code_consumes_blob_token():
    """
    Spec: Vercel Blob provisioned but unconsumed — no application code
    consumes the token in this item (Automatable, narrowed).
    """
    for py_file in _iter_python_files():
        text = py_file.read_text(encoding="utf-8")
        assert "BLOB_READ_WRITE_TOKEN" not in text, py_file
        assert "vercel_blob" not in text, py_file
        assert "blob.vercel-storage.com" not in text, py_file

    import config.settings as settings_module

    # STORAGES now exists (WhiteNoise's staticfiles backend, item #2 fix),
    # but "default" -- where a Blob-consuming override would go -- must
    # still be the plain filesystem backend, never a Blob storage class.
    assert (
        settings_module.STORAGES["default"]["BACKEND"]
        == "django.core.files.storage.FileSystemStorage"
    ), "settings module must not override the default file-storage backend"


def test_a9_env_ignored_and_example_has_no_real_secrets():
    """
    Spec: Secrets handling — .env is gitignored, .env.example carries only
    placeholders, never a real secret (Automatable).
    """
    gitignore_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore_text

    example_path = REPO_ROOT / ".env.example"
    example_text = example_path.read_text(encoding="utf-8")

    # A real Neon connection string embeds a lowercase, hyphenated project
    # slug (e.g. ep-demo-abc123-pooler.eu-central-1.aws.neon.tech); a
    # placeholder host uses an uppercase token like HOST.neon.tech instead,
    # which this pattern does not match.
    assert not re.search(
        r"postgresql://\S+:\S+@ep-[a-z0-9-]+\.\S*neon\.tech", example_text
    ), ".env.example must not contain a real Neon DATABASE_URL credential"

    for line in example_text.splitlines():
        if not line.strip().startswith("DJANGO_SECRET_KEY="):
            continue
        value = line.split("=", 1)[1].strip()
        assert len(value) < 40, ".env.example must not contain a real secret key"
