from dataclasses import asdict
from typing import Any, Dict, Tuple, Optional

from app.layer_4.services import fairness_service
from app.layer_2.use_cases.extract_metadata import ExtractMetadataUseCase, ExtractMetadataResult
from app.layer_1.entities.fair_assessment import FairnessReport
from app.layer_1.entities.software_metadata import SoftwareMetadata


class StubExtractMetadataUseCase:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    def execute(
        self,
        repo_url: str,
        schema: str,
        access_token: Optional[str] = None,
    ) -> ExtractMetadataResult:  # type: ignore[override]
        self.calls.append(
            {
                "repo_url": repo_url,
                "schema": schema,
                "access_token": access_token,
            }
        )
        md = SoftwareMetadata(
            license={"name": "MIT"},  # type: ignore[assignment]
            documentation="https://example.com/docs",  # type: ignore[assignment]
            identifier=["https://doi.org/10.1234/example"],
        )
        jsonld = {
            "license": {"name": "MIT"},
            "documentation": "https://example.com/docs",
            "identifier": ["https://doi.org/10.1234/example"],
        }
        return ExtractMetadataResult(
            jsonld_document=jsonld,
            extraction_metadata={},
            metadata=md,
        )


def test_run_fairness_assessment_uses_usecase_and_metadata(monkeypatch):
    stub_usecase = StubExtractMetadataUseCase()
    monkeypatch.setattr(
        fairness_service,
        "ExtractMetadataUseCase",
        lambda *args, **kwargs: stub_usecase,
    )

    jsonld_document, report = fairness_service.run_fairness_assessment(
        repo_url="https://example.com/repo",
        schema="CODEMETA",
        access_token="token-123",
        with_enrichment=False,
    )

    # Use case was called with expected arguments
    assert stub_usecase.calls
    call = stub_usecase.calls[0]
    assert call["repo_url"] == "https://example.com/repo"
    assert call["schema"] == "CODEMETA"
    assert call["access_token"] == "token-123"

    # JSON-LD is passed through
    assert jsonld_document["license"]["name"] == "MIT"

    # FAIRness report is computed and reusable/findable scores are positive
    assert isinstance(report, FairnessReport)
    assert report.reusable > 0.0
    assert report.findable > 0.0

