"""Tech-atlas schema — pydantic models for atlas entries.

Every entry is a row in the SQLite `entries` table. The `data` JSON column holds
everything except the indexed columns (id, name, domain, entry_type, parent_id).

Design notes:
* Element-level provenance: each item in array fields carries its own `sources` list.
  No top-level field-path indirection — sources travel with the data they support.
* Every fact is traceable: a `Source` has a verbatim `quoted_text` excerpt plus a
  `raw_id` pointer into `data/raw/manifest.json` (gitignored, internal-only).
* Two-layer model: this schema describes Layer 2 (derived seeds). Layer 1 (raw
  cached artifacts) is preserved separately so schema changes can re-extract
  without re-fetching.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Provenance for a single fact or element."""

    raw_id: str
    url: str
    fetched_at: datetime
    quoted_text: str
    ai_or_human: Literal["ai", "human"]
    confidence: float = Field(ge=0.0, le=1.0)


class Innovator(BaseModel):
    name: str
    role: str
    country: str | None = None
    year: int | None = None
    contribution: str | None = None
    recognition_status: Literal["headline", "well_known", "underrecognized", "obscure"] | None = None
    sources: list[Source] = Field(default_factory=list)


class Predecessor(BaseModel):
    """An earlier innovation this one evolved from, competed with, or was inspired by."""

    name: str
    relationship: Literal["evolved_from", "competing_predecessor", "inspiration"]
    year: int | None = None
    brief: str | None = None
    linked_entry_id: str | None = None
    sources: list[Source] = Field(default_factory=list)


class EnablingComponent(BaseModel):
    """Parallel infrastructure / tech / practice required for the innovation to work or scale."""

    name: str
    type: Literal["technology", "infrastructure", "practice", "process", "standard"]
    role: str
    brief: str | None = None
    linked_entry_id: str | None = None
    sources: list[Source] = Field(default_factory=list)


class FailedAlternative(BaseModel):
    name: str
    why_failed: str
    period: str | None = None
    sources: list[Source] = Field(default_factory=list)


class Funder(BaseModel):
    entity: str
    type: Literal["private", "government", "philanthropic", "venture", "public_subscription", "other"]
    period: str | None = None
    brief: str | None = None
    sources: list[Source] = Field(default_factory=list)


class RegulatoryMoment(BaseModel):
    year: int
    jurisdiction: str
    description: str
    effect: Literal["enabling", "restricting", "neutral", "mixed"] | None = None
    sources: list[Source] = Field(default_factory=list)


class GeographicDiffusion(BaseModel):
    place: str
    year: int
    milestone: Literal["first", "1pct", "10pct", "saturation"]
    brief: str | None = None
    sources: list[Source] = Field(default_factory=list)


class KeyDate(BaseModel):
    year: int
    event: str
    event_type: Literal["invention", "patent", "scaling", "regulatory", "adoption"]
    significance: str | None = None
    sources: list[Source] = Field(default_factory=list)


class Entry(BaseModel):
    """A single atlas entry — category, variant, independent topic, or brief stub.

    `entry_type` describes the entry itself, not its role in another entry's story:
      * category — has variants (e.g., bus)
      * variant  — child of a category (e.g., bus:motorized_diesel)
      * topic    — independent entry (e.g., transit_system:bus_rapid_transit)
      * stub     — intentionally brief entry, often referenced by others (e.g., tire:pneumatic_tire)

    "Component" is a relationship surfaced via enabling_components / backlinks, NOT a type.
    Entry IDs follow `<kind>:<specific>` so the prefix names what the technology IS, not
    the role it plays in some other entry's story.
    """

    id: str
    name: str
    domain: str
    description: str
    entry_type: Literal["category", "variant", "topic", "stub"]
    parent_id: str | None = None

    description_sources: list[Source] = Field(default_factory=list)
    innovators: list[Innovator] = Field(default_factory=list)
    predecessors: list[Predecessor] = Field(default_factory=list)
    enabling_components: list[EnablingComponent] = Field(default_factory=list)
    failed_alternatives: list[FailedAlternative] = Field(default_factory=list)
    funders: list[Funder] = Field(default_factory=list)
    regulatory_moments: list[RegulatoryMoment] = Field(default_factory=list)
    geographic_diffusion: list[GeographicDiffusion] = Field(default_factory=list)
    key_dates: list[KeyDate] = Field(default_factory=list)
