import base64
import pytest
from unittest.mock import Mock
from app.layer_3.plugins.url_pattern_matcher_plugin import URLPatternMatcher
from app.layer_3.plugins.shared.bibtex import parse_bibtex
from app.layer_3.plugins.shared.utils import iso_dt_to_str
from app.layer_3.plugins.shared.git_platform_client import FileNotFoundOnPlatformError
from app.layer_3.plugins.github.github_client import GitHubClient, GitHubRepositoryFile
from app.layer_3.plugins.gitlab.gitlab_client import GitLabClient, GitLabRepositoryItem
from app.layer_3.plugins.codeberg.codeberg_client import CodebergClient, CodebergRepositoryFile

def test_url_pattern_matcher_platform_repo_and_zenodo_badges(repo_urls):
    assert URLPatternMatcher.detect_platform(repo_urls["github"]) == "github"
    assert URLPatternMatcher.detect_platform(repo_urls["gitlab"]) == "gitlab"
    assert URLPatternMatcher.detect_platform("https://example.org/a/b") is None
    assert URLPatternMatcher.extract_repo_info(repo_urls["github"]) == ("acme", "widget")
    text='[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.123.svg)](https://doi.org/10.5281/zenodo.123)'
    assert URLPatternMatcher.check_zenodo_badge(text) == ["https://doi.org/10.5281/zenodo.123"]
    assert URLPatternMatcher.check_zenodo_badge("https://doi.org/10.1/bare") == []

def test_shared_helpers_parse_bibtex_and_dates():
    e = parse_bibtex('@article{x, title={Nested {Title}}, author="Doe, Jane"}')[0]
    assert e["type"] == "article" and e["fields"]["title"] == "Nested {Title}"
    assert iso_dt_to_str("2024-01-02T03:04:05Z") == "2024-01-02"
    with pytest.raises(TypeError): iso_dt_to_str(None)

def test_github_client_parsing_headers_and_base64(context, fake_response):
    c = GitHubClient(context, __import__('app.layer_2.contracts', fromlist=['ExtractionState']).ExtractionState(__import__('app.layer_1.metadata_collector.metadata_collector', fromlist=['MetadataCollector']).MetadataCollector()))
    assert c._build_headers()["Authorization"] == "token secret"
    assert c._extract_repository_info(context) == ("acme", "widget")
    assert c._get_api_base_url() == "https://api.github.com"
    assert GitHubRepositoryFile({"name":"x","path":"x","type":"file","content":base64.b64encode(b"hello").decode(),"encoding":"base64"}).get_content() == "hello"
    c._caching_get = Mock(return_value=fake_response([], 404))
    with pytest.raises(FileNotFoundOnPlatformError): c.list_directory()

def test_gitlab_client_parsing_nested_namespace_headers(context):
    from app.layer_2.contracts import ExtractionContext, ExtractionState
    from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
    ctx = ExtractionContext("https://gitlab.com/acme/group/widget/-/tree/main", "software", context.schema, "gitlab.com", "tok")
    c = GitLabClient(ctx, ExtractionState(MetadataCollector()))
    assert c._extract_repository_info(ctx) == ("acme/group", "widget")
    assert c._build_headers()["Authorization"] == "Bearer tok"
    assert c.get_project_id() == "acme%2Fgroup%2Fwidget"
    assert GitLabRepositoryItem({"name":"README","path":"README","type":"blob"}).is_dir is False

def test_codeberg_client_headers_and_invalid_url(context):
    from app.layer_2.contracts import ExtractionContext, ExtractionState
    from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
    ctx = ExtractionContext("https://codeberg.org/acme/widget.git", "software", context.schema, "codeberg.org", "tok")
    c = CodebergClient(ctx, ExtractionState(MetadataCollector()))
    assert c._extract_repository_info(ctx) == ("acme", "widget")
    assert c._build_headers()["Authorization"] == "token tok"
    with pytest.raises(ValueError): c._extract_repository_info(ExtractionContext("", "software", context.schema))
    assert CodebergRepositoryFile({"name":"x","path":"x","type":"file","content":"bad","encoding":"base64"}).get_content() is None
