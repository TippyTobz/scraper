from dataclasses import dataclass
from typing import Optional


@dataclass
class JobResult:
    """
    Normalised job result returned by any provider.
    Every provider must map its own response fields to these.
    """
    title: str
    company: str
    location: str
    apply_url: str


class JobProvider:
    """
    Abstract base class for job data providers.

    To add a new provider (e.g. HiringCafe):
        1. Create a new file in this directory e.g. hiring_cafe.py
        2. Subclass JobProvider and implement search()
        3. Update job_service.py to instantiate the new provider
    """

    async def search(self, role: str, limit: int = 5) -> list[JobResult]:
        raise NotImplementedError("Job providers must implement search()")
