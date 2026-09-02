import tempfile
import os
import re
from scancode.api import get_licenses

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

_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_ANGLE_BRACKET_RE = re.compile(r'<[^>]*>')
_MD_EMPHASIS_RE = re.compile(r'[*_`]+')
_NAME_HEADER_ALIASES = {"name", "contributor", "contributors", "full name", "contributor name", "author"}
_BULLET_RE = re.compile(r'^[-*\u2022]\s+')      
_NUMBERED_RE = re.compile(r'^\d+[.)]\s+')        
_SEPARATOR_SPLIT_RE = re.compile(r'\s+[-\u2013]\s+')
_TRAILING_PAREN_RE = re.compile(r'\s*\([^)]*\)\s*$')
_TRAILING_HANDLE_RE = re.compile(r'(\s+@\S+)+$')


def _clean_cell(text: str) -> str:
    """Strips markdown link syntax (keeping the link text), <...> spans
    (emails or autolinked urls), and emphasis markers from a single table
    cell or line."""
    text = _MD_LINK_RE.sub(r'\1', text)
    text = _ANGLE_BRACKET_RE.sub('', text)
    text = _MD_EMPHASIS_RE.sub('', text)
    return text.strip()


def _parse_markdown_table_names(lines: list[str]) -> list[str]:
    """Parses every markdown table found in `lines` and returns the values
    of whichever column looks like a name/contributor column, per table.
    Handles multiple tables in one file (e.g. one per release). Returns []
    if no table with a recognizable name column is found."""
    names = []
    i = 0
    while i < len(lines) - 1:
        header_line, sep_line = lines[i], lines[i + 1]
        is_table_header = (
            "|" in header_line
            and re.fullmatch(r'\s*\|?[\s:|-]+\|?\s*', sep_line) is not None
            and "-" in sep_line
        )
        if not is_table_header:
            i += 1
            continue

        headers = [_clean_cell(h).lower() for h in header_line.strip().strip("|").split("|")]
        name_col = next((idx for idx, h in enumerate(headers) if h in _NAME_HEADER_ALIASES), None)
        i += 2  # skip header + separator row
        if name_col is None:
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            continue

        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = lines[i].strip().strip("|").split("|")
            if name_col < len(cells):
                name = _clean_cell(cells[name_col])
                if name:
                    names.append(name)
            i += 1
    return names


def _parse_bullet_list_names(lines: list[str]) -> list[str]:
    """Fallback for CONTRIBUTORS files that are plain bulleted/numbered
    lists rather than tables. Handles, per line, in order:
      - a bullet/number marker to strip
      - the whole line being a single markdown link (link text -> name)
      - one or more <email> / <url> spans to drop
      - a "Name - role - url" convention (keeps text before first " - ")
      - a trailing "(@handle on Github)" / "(Affiliation)" parenthetical
      - a trailing bare "@handle" with no brackets
    """
    names = []
    for line in lines:
        if not (_BULLET_RE.match(line) or _NUMBERED_RE.match(line)):
            continue
        line = _BULLET_RE.sub('', line)
        line = _NUMBERED_RE.sub('', line)
        line = _MD_LINK_RE.sub(r'\1', line)
        line = _ANGLE_BRACKET_RE.sub('', line)
        line = _MD_EMPHASIS_RE.sub('', line)
        parts = _SEPARATOR_SPLIT_RE.split(line, maxsplit=1)
        name = parts[0]
        name = _TRAILING_PAREN_RE.sub('', name)
        name = _TRAILING_HANDLE_RE.sub('', name)
        name = name.rstrip(' -\u2013').strip()
        if name and not name.startswith("#"):
            names.append(name)
    return names


def parse_contributor_names(content: str) -> list[str]:
    """Best-effort extraction of contributor names/handles from a CONTRIBUTORS(.md) file.

    CONTRIBUTORS files have no standard format. This handles the shapes seen most often in practice:
      - markdown tables with a Name/Contributor/Author column (possibly
        several tables in one file, e.g. one per release)
      - bulleted or numbered lists: bare "- Name", "- Name <email>"
        (possibly several emails), "- Name - role - url", "- Name @handle",
        "- Name (@handle on Github)", or "- [Name (Org)](url)"

    Limitations, by design rather than oversight:
      - if a table's "name" column only contains linked GitHub handles
        (no real human name anywhere in the file), the handle is returned
        as-is -- callers should not assume the result is always a real name
      - multiple tables/sections are not distinguished semantically (e.g.
        a "Reports"/bug-tracker table is extracted the same as a "Code"/
        merged-PRs table); there is no reliable, format-agnostic way to
        infer that distinction from arbitrary heading text
      - always treat the result as a low-confidence signal, never
        authoritative
    """
    lines = content.splitlines()
    table_names = _parse_markdown_table_names(lines)
    if table_names:
        return table_names
    return _parse_bullet_list_names(lines)