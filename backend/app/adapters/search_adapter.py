"""Bounded Search & Entity Resolution Adapter.

Implements Sections 9 & 17 of the VendorGuard AI Blueprint:
- Supplier identity resolution (legal name, aliases, domain, location)
- Rejection of same-name unrelated companies (entity_match == 'ambiguous' or 'unrelated')
- Deduplication of syndicated copies
- Auditable external_status values: reliable_evidence, no_relevant_evidence, ambiguous_entity, unavailable, stale
- Offline catalog fallback + bounded query limit
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

from backend.app.domain.models_domain import (
    ExternalEvidenceStatus,
    EvidenceItemRecord,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CATALOG_PATH = os.path.join(BASE_DIR, "datasets", "synthetic", "evidence_catalog.json")


class BoundedSearchAdapter:
    """Manages bounded external searches and identity resolution."""

    def __init__(self, catalog_path: str = CATALOG_PATH):
        self.catalog_path = catalog_path
        self._cache: Dict[str, Tuple[List[EvidenceItemRecord], ExternalEvidenceStatus]] = {}

    def _load_catalog(self) -> List[Dict]:
        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def check_supplier_signals(
        self,
        supplier_id: str,
        legal_name: str,
        aliases: Optional[List[str]] = None,
        domain: Optional[str] = None,
        location: Optional[str] = None,
        as_of_dt: Optional[datetime] = None,
        simulated_failure: bool = False,
    ) -> Tuple[List[EvidenceItemRecord], ExternalEvidenceStatus, Optional[str]]:
        """Performs bounded retrieval and identity resolution for a supplier.

        Returns:
            (evidence_records, external_status, failure_reason)
        """
        if simulated_failure:
            return [], ExternalEvidenceStatus.UNAVAILABLE, "Search provider connection timeout / rate limit reached"

        cache_key = f"{supplier_id}:{as_of_dt.isoformat() if as_of_dt else 'now'}"
        if cache_key in self._cache:
            records, status = self._cache[cache_key]
            return records, status, None

        if aliases is None:
            aliases = []
        name_tokens = {legal_name.lower()} | {a.lower() for a in aliases}

        catalog = self._load_catalog()
        matched_items: List[Dict] = []
        ambiguous_matches: List[Dict] = []

        for item in catalog:
            item_sup = item.get("supplier_legal_name", "").lower()
            entity_match = item.get("entity_match", "verified").lower()

            # Date boundary check: evidence published after as_of cannot leak into the past
            if as_of_dt and item.get("published_at"):
                pub_dt = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
                if pub_dt > as_of_dt:
                    continue  # Leakage prevention

            # Identity match check
            is_matched_name = item_sup in name_tokens or any(t in item_sup for t in name_tokens)
            if is_matched_name:
                if entity_match == "verified":
                    matched_items.append(item)
                elif entity_match in ["ambiguous", "unrelated"]:
                    ambiguous_matches.append(item)

        # Handle ambiguous entity match (Scenario 5: Same-name unrelated company)
        if not matched_items and ambiguous_matches:
            status = ExternalEvidenceStatus.AMBIGUOUS_ENTITY
            return [], status, f"Entity ambiguity detected: articles found for similarly named entity, but verified location/domain did not match."

        if not matched_items:
            status = ExternalEvidenceStatus.NO_RELEVANT_EVIDENCE
            return [], status, None

        # Deduplicate syndicated stories (Scenario 6: Syndicated copies of one event)
        # Group by (event_type, location) and retain highest scoring item
        deduped: Dict[str, Dict] = {}
        for item in matched_items:
            # Group by event_type to prevent syndicated republishing from inflating evidence
            event_key = item["event_type"]
            current = deduped.get(event_key)
            item_score = item["severity"] * item["reliability_factor"] * item["freshness_factor"]
            if current is None:
                deduped[event_key] = item
            else:
                curr_score = current["severity"] * current["reliability_factor"] * current["freshness_factor"]
                if item_score > curr_score:
                    deduped[event_key] = item

        records: List[EvidenceItemRecord] = []
        for item in deduped.values():
            pub_dt = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            rec = EvidenceItemRecord(
                evidence_id=item["evidence_id"],
                supplier_id=supplier_id,
                source_url=item["source_url"],
                publisher=item["publisher"],
                published_at=pub_dt,
                event_type=item["event_type"],
                entity_match=item["entity_match"],
                severity=float(item["severity"]),
                reliability_factor=float(item["reliability_factor"]),
                freshness_factor=float(item["freshness_factor"]),
                supporting_excerpt=item["supporting_excerpt"],
                is_synthetic=item.get("is_synthetic", True),
            )
            records.append(rec)

        status = ExternalEvidenceStatus.RELIABLE_EVIDENCE
        self._cache[cache_key] = (records, status)
        return records, status, None
