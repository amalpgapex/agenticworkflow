"""CARE 701B workflow schemas (`Name@version`)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ForbidModel(BaseModel):
    """Reject unknown keys."""

    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# Step 1: PDF Intake & Extraction
# -----------------------------------------------------------------------------


class ConfidenceScores(ForbidModel):
    """Confidence scores for extracted fields."""

    member_ssn: float = Field(ge=0.0, le=1.0)
    member_name: float = Field(ge=0.0, le=1.0)
    member_dob: float = Field(ge=0.0, le=1.0)
    document_date: float = Field(ge=0.0, le=1.0)
    initial_checkbox: float = Field(ge=0.0, le=1.0)

    @property
    def min(self) -> float:
        """Return the minimum confidence score."""
        return min(
            self.member_ssn,
            self.member_name,
            self.member_dob,
            self.document_date,
            self.initial_checkbox,
        )


class Care701bExtraction(ForbidModel):
    """Extracted fields from CARE 701B PDF form."""

    # Core extracted fields
    member_ssn: str = Field(description="Member SSN (format: XXX-XX-XXXX)")
    member_name: str = Field(description="Member full name")
    member_dob: date = Field(description="Member date of birth")
    document_date: date = Field(description="Document date")
    form_type: str = Field(default="CARE-701B", description="Form type identifier")

    # Validation fields
    initial_checkbox_checked: bool = Field(description="Whether 'Initial' checkbox is checked")
    confidence_scores: ConfidenceScores = Field(description="OCR confidence per field")

    # Metadata
    source_file_key: str = Field(description="S3 key of source PDF")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    low_confidence: bool = Field(default=False, description="True if any field < 0.85 confidence")


# -----------------------------------------------------------------------------
# Step 2: Member Validation
# -----------------------------------------------------------------------------


class MemberValidationResult(ForbidModel):
    """Result of TrueCare member lookup."""

    member_found: bool = Field(description="Whether member was found in TrueCare")
    member_id: str | None = Field(default=None, description="TrueCare member ID if found")
    match_type: Literal["exact", "partial", "none"] = Field(
        default="none", description="Type of match found"
    )
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = Field(default=None, description="Error message if lookup failed")


# -----------------------------------------------------------------------------
# Step 3: Duplicate Check
# -----------------------------------------------------------------------------


class DuplicateMatch(ForbidModel):
    """A matching document found in duplicate check."""

    document_id: str
    document_date: date
    similarity_score: float = Field(ge=0.0, le=1.0)


class DuplicateCheckResult(ForbidModel):
    """Result of 12-month duplicate document check."""

    is_duplicate: bool = Field(description="Whether a duplicate was found")
    matches: list[DuplicateMatch] = Field(
        default_factory=list, description="List of matching documents"
    )
    lookback_start: date = Field(description="Start of lookback window")
    lookback_end: date = Field(description="End of lookback window (today)")
    check_timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Step 4: Document Upload
# -----------------------------------------------------------------------------


class DocumentUploadResult(ForbidModel):
    """Result of uploading document to TrueCare."""

    upload_success: bool = Field(description="Whether upload succeeded")
    document_id: str | None = Field(default=None, description="TrueCare document ID")
    attachment_confirmed: bool = Field(
        default=False, description="Whether attachment to member was confirmed"
    )
    storage_url: str | None = Field(default=None, description="TrueCare storage URL")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = Field(default=None, description="Error message if upload failed")


# -----------------------------------------------------------------------------
# Step 5: Case Note Creation
# -----------------------------------------------------------------------------


class CaseNoteResult(ForbidModel):
    """Result of creating a case note in TrueCare."""

    note_created: bool = Field(description="Whether note was created successfully")
    note_id: str | None = Field(default=None, description="TrueCare case note ID")
    note_content: str = Field(description="The generated case note text")
    template_used: str = Field(default="CARE-701B-STANDARD", description="Template identifier")
    created_timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = Field(default=None, description="Error message if creation failed")


# -----------------------------------------------------------------------------
# Step 6: PHI-Compliant Logging
# -----------------------------------------------------------------------------


class LogEntry(ForbidModel):
    """A single PHI-compliant log entry."""

    batch_id: str
    member_id: str  # Only identifier, not SSN
    document_id: str
    note_id: str
    status: Literal["completed", "failed", "pending_review"]
    timestamp: datetime
    processing_duration_ms: int | None = None
    error_code: str | None = None


class LogResult(ForbidModel):
    """Result of writing to the output log."""

    log_written: bool = Field(description="Whether log entry was written")
    log_key: str | None = Field(default=None, description="S3 key of log file")
    entry: LogEntry | None = Field(default=None, description="The written log entry")
    write_timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Action Step Results (for type: action steps)
# -----------------------------------------------------------------------------


class ActionResult(ForbidModel):
    """Generic result for action steps (direct tool calls)."""

    success: bool = Field(description="Whether the action succeeded")
    data: dict = Field(default_factory=dict, description="Action output data")
    error: str | None = Field(default=None, description="Error message if failed")
    tool_name: str = Field(description="Name of the tool that was called")
    duration_ms: int | None = Field(default=None, description="Execution duration in milliseconds")
