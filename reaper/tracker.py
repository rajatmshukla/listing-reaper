from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_STATUSES = {"shortlisted", "applied", "skipped", "rejected"}


class StateError(Exception):
    """Raised when the tracking state file is corrupt, invalid, or cannot be accessed."""


@dataclass
class TrackedRecord:
    """A tracked record of a job listing."""

    dedupe_key: str
    listing_id: str
    first_seen: str
    last_seen: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "status": self.status,
        }


class Tracker:
    """Persistent tracking of seen and acted-upon listings.

    Ensures atomic file operations and protects against corrupt state resets.
    """

    def __init__(
        self,
        records: dict[str, TrackedRecord] | None = None,
        version: int = 1,
    ) -> None:
        self.records: dict[str, TrackedRecord] = dict(records or {})
        self.version = version

    @classmethod
    def load(cls, path: str | Path) -> Tracker:
        """Load tracker from an existing JSON state file.

        Raises:
            FileNotFoundError: If the file does not exist.
            StateError: If the file is corrupt, unreadable, or violates the schema.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"State file not found: {path}")

        try:
            raw_text = path_obj.read_text(encoding="utf-8")
        except Exception as err:
            raise StateError(f"Cannot read state file '{path}': {err}") from err

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as err:
            raise StateError(f"State file '{path}' is corrupt: invalid JSON: {err}") from err

        if not isinstance(data, dict):
            raise StateError(f"State file '{path}' is corrupt: root must be a JSON object.")

        version = int(data.get("version", 1))

        if "seen" in data:
            if not isinstance(data["seen"], dict):
                raise StateError(f"State file '{path}' is corrupt: 'seen' must be an object.")
            raw_records = data["seen"]
        elif "records" in data:
            if not isinstance(data["records"], dict):
                raise StateError(f"State file '{path}' is corrupt: 'records' must be an object.")
            raw_records = data["records"]
        else:
            raw_records = {k: v for k, v in data.items() if k != "version"}

        records: dict[str, TrackedRecord] = {}
        for key, val in raw_records.items():
            if not isinstance(val, dict):
                raise StateError(
                    f"State file '{path}' is corrupt: record for '{key}' must be an object."
                )
            status = str(val.get("status") or "").strip()
            if status and status not in VALID_STATUSES:
                raise StateError(
                    f"State file '{path}' is corrupt: invalid status '{status}' for '{key}'. "
                    f"Valid statuses are: {sorted(VALID_STATUSES)}"
                )
            records[key] = TrackedRecord(
                dedupe_key=key,
                listing_id=str(val.get("listing_id") or "").strip(),
                first_seen=str(val.get("first_seen") or "").strip(),
                last_seen=str(val.get("last_seen") or "").strip(),
                status=status,
            )

        return cls(records=records, version=version)

    @classmethod
    def load_or_empty(cls, path: str | Path) -> Tracker:
        """Load state if file exists, or return an empty Tracker if not found.

        Corrupt files will raise StateError and are never silently reset.
        """
        path_obj = Path(path)
        if path_obj.exists():
            return cls.load(path_obj)
        return cls()

    def has(self, key: str) -> bool:
        """Check whether dedupe key has been recorded."""
        return key in self.records

    def get(self, key: str) -> TrackedRecord | None:
        """Retrieve record by dedupe key."""
        return self.records.get(key)

    def find_by_id(self, listing_id: str) -> TrackedRecord | None:
        """Find record by listing ID."""
        for rec in self.records.values():
            if rec.listing_id == listing_id:
                return rec
        return None

    def record(
        self,
        key: str,
        status: str,
        date: str,
        listing_id: str = "",
    ) -> None:
        """Record or update a listing's status and date."""
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Valid statuses: {sorted(VALID_STATUSES)}"
            )

        if key in self.records:
            rec = self.records[key]
            rec.status = status
            rec.last_seen = date
            if listing_id and not rec.listing_id:
                rec.listing_id = listing_id
        else:
            self.records[key] = TrackedRecord(
                dedupe_key=key,
                listing_id=listing_id,
                first_seen=date,
                last_seen=date,
                status=status,
            )

    def update_by_id(
        self,
        listing_id: str,
        status: str,
        date: str,
    ) -> tuple[str, str, str]:
        """Update status for a listing by ID.

        Returns:
            A tuple of (dedupe_key, previous_status, new_status).

        Raises:
            ValueError: If status is invalid.
            KeyError: If listing_id is not found in state.
        """
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Valid statuses: {sorted(VALID_STATUSES)}"
            )

        rec = self.find_by_id(listing_id)
        if rec is None:
            raise KeyError(f"Listing ID '{listing_id}' not found in state.")

        prev_status = rec.status
        rec.status = status
        rec.last_seen = date
        return rec.dedupe_key, prev_status, status

    def save(self, path: str | Path) -> None:
        """Atomically persist state to disk via a temporary file and os.replace."""
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": self.version,
            "seen": {k: rec.to_dict() for k, rec in sorted(self.records.items())},
        }

        # Write to temporary file in the same directory to allow atomic os.replace
        temp_file = path_obj.with_name(f".{path_obj.name}.tmp.{os.getpid()}")
        try:
            temp_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(temp_file, path_obj)
        except Exception:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise
