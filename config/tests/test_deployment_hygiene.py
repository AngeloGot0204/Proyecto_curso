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


def test_a7_blob_consumption_scoped_to_storage_module():
    """
    Spec: Vercel Blob is now consumed (backlog #14 follow-up: production's
    read-only filesystem cannot persist uploads, so config/storage.py wraps
    the vercel_blob client) — but ONLY from that one module, never scattered
    across the app.
    """
    allowed = {REPO_ROOT / "config" / "storage.py"}

    for py_file in _iter_python_files():
        if py_file in allowed:
            continue
        text = py_file.read_text(encoding="utf-8")
        assert "vercel_blob" not in text, py_file
        assert "blob.vercel-storage.com" not in text, py_file
        if py_file.name != "settings.py":
            # settings.py legitimately reads the env var name to pick a
            # storage backend, without importing the blob client itself.
            assert "BLOB_READ_WRITE_TOKEN" not in text, py_file

    import config.settings as settings_module

    # The default backend now switches to Blob storage in production (not
    # DEBUG), and stays FileSystemStorage locally/in tests.
    assert settings_module.STORAGES["default"]["BACKEND"] in (
        "django.core.files.storage.FileSystemStorage",
        "config.storage.VercelBlobStorage",
    ), "settings module must only ever select one of these two backends"


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


def test_a15_vercelignore_excluye_los_archivos_de_entorno():
    """SECURITY-REPORT.md F-12: `.gitignore` keeps `.env` out of the repo,
    and `test_a9` proves it. Deployments are a separate path: when a
    `.vercelignore` exists the Vercel CLI reads it INSTEAD of `.gitignore`
    to decide what to upload, so the exclusion has to be restated there.
    Vercel also skips `.env` by default; this asserts we do not depend on
    that default staying true."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    lineas = {
        linea.strip()
        for linea in (raiz / ".vercelignore").read_text(encoding="utf-8").splitlines()
    }

    assert ".env" in lineas
    assert ".env.*" in lineas
    assert "!.env.example" in lineas
