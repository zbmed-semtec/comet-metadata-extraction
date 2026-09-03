import datetime
import re
import tempfile
import os
from scancode.api import get_licenses

from dateutil import parser as date_parser


def iso_dt_to_str(iso_dt):
    """Convert an ISO 8601 or near-ISO 8601 datetime to a 'YYYY-MM-DD' date string.

    Uses `dateutil.parser.parse`, which is highly tolerant of real-world
    datetime formatting inconsistencies commonly found in third-party
    metadata sources (e.g. codemeta.json, platform APIs), including:
      - Trailing 'Z' (Zulu/UTC) suffix.
      - Malformed strings combining both 'Z' and a numeric UTC offset
        (e.g. '2018-04-16T10:54:22Z+0200'), which are invalid per ISO 8601
        but occasionally found in the wild.
      - Missing colons in UTC offsets (e.g. '+0200' instead of '+02:00').
      - Various other loosely-formatted date/time strings.

    Args:
        iso_dt: A datetime string (ISO 8601 or a close variant), or an
            object whose `str()` representation is such a string.

    Returns:
        str: The date portion of the parsed datetime, formatted as 'YYYY-MM-DD'.

    Raises:
        ValueError: If `iso_dt` is empty/blank, or cannot be parsed as a
            valid datetime.
        TypeError: If `iso_dt` is `None`.
    """
    if iso_dt is None:
        raise TypeError("iso_dt must not be None")

    s = str(iso_dt).strip()
    if not s:
        raise ValueError("iso_dt must not be empty")

    # Malformed: stray 'Z' immediately followed by a numeric UTC offset,
    # e.g. '2018-04-16T10:54:22Z+0200'. dateutil treats 'Z' as UTC and
    # would otherwise choke on (or silently mishandle) the trailing offset,
    # so we strip the redundant 'Z' and keep the explicit offset.
    s = re.sub(r'Z(?=[+-]\d{2}:?\d{2}$)', '', s)

    try:
        dt = date_parser.parse(s)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Could not parse datetime string: {iso_dt!r}") from exc

    return str(dt.date())

def match_license_text(text: str):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    try:
        results = get_licenses(tmp_path)
        return results
    finally:
        os.remove(tmp_path)

dependency_files = {
    # Python
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "pipfile", "pipfile.lock", "poetry.lock", "environment.yml",
    # JavaScript / Node
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    # Ruby
    "gemfile", "gemfile.lock",
    # Rust
    "cargo.toml", "cargo.lock",
    # Go
    "go.mod", "go.sum",
    # Java / JVM
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.lockfile",
    # PHP
    "composer.json", "composer.lock",
    # .NET
    "packages.config", "*.csproj",
    # C/C++
    "conanfile.txt", "conanfile.py", "vcpkg.json",
    # Other
    "mix.exs", "mix.lock",  # Elixir
    "dependencies.yaml",    # Generic
}