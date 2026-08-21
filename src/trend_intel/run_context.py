"""Identity for a single pipeline run.

The old scripts recovered "when was this collected?" by regex-parsing it back
out of a filename, which meant the answer could differ between two files that
came from the same run. A RunContext is created exactly once per run and
stamped onto every raw file, every processed row, and every log line.

In Phase 3 the run_id becomes the deduplication key in BigQuery: re-running
the pipeline produces a new run_id, so a failed load can be retried without
double-counting, and any row can be traced back to the exact fetch that
produced it.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RunContext:
    """Immutable identity and timestamp for one execution of the pipeline."""

    run_id: str
    collected_at: datetime

    @classmethod
    def create(cls) -> "RunContext":
        """Start a new run. Call this once, at the top of the pipeline."""
        return cls(
            run_id=str(uuid.uuid4()),
            collected_at=datetime.now(timezone.utc),
        )

    @property
    def timestamp_slug(self) -> str:
        """Filename-safe UTC timestamp, e.g. 20260821_140817."""
        return self.collected_at.strftime("%Y%m%d_%H%M%S")

    @property
    def short_id(self) -> str:
        """First 8 characters of the run_id, for readable log lines."""
        return self.run_id[:8]

    def as_metadata(self) -> dict[str, str]:
        """Lineage fields to embed in every raw artifact."""
        return {
            "run_id": self.run_id,
            "collected_at": self.collected_at.isoformat(),
        }
