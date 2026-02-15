"""
Data models for papers and their accessibility status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class AccessibilityStatus(str, Enum):
    """Status of paper accessibility"""
    UNKNOWN = "unknown"
    PUBLIC = "public"
    RESTRICTED = "restricted"
    REQUIRES_LOGIN = "requires_login"
    PAYWALLED = "paywalled"
    NOT_FOUND = "not_found"
    ERROR = "error"
    HUMAN_ERROR = "human_error"


class ResourceType(str, Enum):
    """Type of academic resource"""
    PAPER = "paper"
    THESIS = "thesis"
    REPORT = "report"
    REFERENCE = "reference"
    PREPRINT = "preprint"
    BOOK_CHAPTER = "book_chapter"


@dataclass
class Paper:
    """Represents an academic paper, thesis, or report"""
    
    # Basic information
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    resource_type: ResourceType = ResourceType.PAPER
    
    # Identifiers
    doi: Optional[str] = None
    url: Optional[str] = None
    arxiv_id: Optional[str] = None
    
    # Publication details
    journal: Optional[str] = None
    conference: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    
    # Accessibility information
    accessibility_status: AccessibilityStatus = AccessibilityStatus.UNKNOWN
    last_checked: Optional[datetime] = None
    download_url: Optional[str] = None
    requires_authentication: bool = False
    authentication_service: Optional[str] = None  # e.g., "ResearchGate", "IEEE", etc.
    
    # Download workflow fields
    section_path: Optional[str] = None  # Full section hierarchy from README (e.g., "Prospectivity/Oceania/Australia")
    final_resolved_url: Optional[str] = None  # Final URL after following redirects
    download_success: bool = False  # Whether download succeeded
    unseen_tag: bool = False  # Whether paper was tagged [UNSEEN] in README
    duplicate_of: Optional[int] = None  # CSV row ID of first occurrence if duplicate
    url_resolvable: bool = False  # Whether URL resolves successfully
    
    # Local storage
    local_file_path: Optional[str] = None
    
    # Metadata
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    # Database fields
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert paper to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "resource_type": self.resource_type.value if self.resource_type else None,
            "doi": self.doi,
            "url": self.url,
            "arxiv_id": self.arxiv_id,
            "journal": self.journal,
            "conference": self.conference,
            "publisher": self.publisher,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "accessibility_status": self.accessibility_status.value if self.accessibility_status else None,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "download_url": self.download_url,
            "requires_authentication": self.requires_authentication,
            "authentication_service": self.authentication_service,
            "section_path": self.section_path,
            "final_resolved_url": self.final_resolved_url,
            "download_success": self.download_success,
            "unseen_tag": self.unseen_tag,
            "duplicate_of": self.duplicate_of,
            "url_resolvable": self.url_resolvable,
            "local_file_path": self.local_file_path,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        """Create paper from dictionary"""
        # Convert string enums back to enum types
        if "resource_type" in data and data["resource_type"]:
            data["resource_type"] = ResourceType(data["resource_type"])
        if "accessibility_status" in data and data["accessibility_status"]:
            data["accessibility_status"] = AccessibilityStatus(data["accessibility_status"])
        
        # Convert ISO format strings back to datetime
        for field_name in ["last_checked", "created_at", "updated_at"]:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
