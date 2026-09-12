from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Iterator, Protocol

from reaper.model import Listing, ListingError


class Source(Protocol):
    """Protocol for fixture or live listing sources."""

    name: str

    def pages(self, page_size: int) -> Iterator[list[Listing]]:
        """Yield pages of listings of up to page_size items."""
        ...


class FixtureSource:
    """Loads local listing fixtures from .jsonl or .csv files.

    Malformed records are recorded in FixtureSource.errors (file, line number, message)
    and never silently skipped.
    """

    def __init__(
        self,
        path: str | Path,
        seed: int | None = None,
        field_map: dict[str, str] | None = None,
    ) -> None:
        self.path = Path(path)
        self.name = self.path.name
        self.errors: list[tuple[str, int, str]] = []
        self.listings: list[Listing] = []
        self._seed = seed
        self.field_map = dict(field_map) if field_map else None

        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Fixture file not found: {self.path}")

        suffix = self.path.suffix.lower()
        if suffix == ".jsonl":
            self._load_jsonl()
        elif suffix == ".csv":
            self._load_csv()
        else:
            raise ValueError(
                f"Unsupported fixture format '{suffix}' for {self.path}. Supported: .jsonl, .csv"
            )

        if self._seed is not None:
            rng = random.Random(self._seed)
            # Create a shallow copy before shuffling
            shuffled = list(self.listings)
            rng.shuffle(shuffled)
            self.listings = shuffled

    def _load_jsonl(self) -> None:
        with self.path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                    if not isinstance(data, dict):
                        self.errors.append(
                            (str(self.path), line_no, "Line is not a valid JSON object.")
                        )
                        continue
                    listing = Listing.from_dict(data, field_map=self.field_map)
                    self.listings.append(listing)
                except json.JSONDecodeError as err:
                    self.errors.append(
                        (str(self.path), line_no, f"JSON decode error: {err}")
                    )
                except ListingError as err:
                    self.errors.append(
                        (str(self.path), line_no, f"Listing validation error: {err}")
                    )
                except Exception as err:
                    self.errors.append(
                        (str(self.path), line_no, f"Unexpected record error: {err}")
                    )

    def _load_csv(self) -> None:
        with self.path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row_no, row in enumerate(reader, start=2):  # 1 is header
                try:
                    listing = Listing.from_dict(row, field_map=self.field_map)
                    self.listings.append(listing)
                except ListingError as err:
                    self.errors.append(
                        (str(self.path), row_no, f"Listing validation error: {err}")
                    )
                except Exception as err:
                    self.errors.append(
                        (str(self.path), row_no, f"Unexpected record error: {err}")
                    )

    def pages(self, page_size: int) -> Iterator[list[Listing]]:
        """Yield pages of listings of size page_size."""
        if page_size <= 0:
            page_size = 10
        for i in range(0, len(self.listings), page_size):
            yield self.listings[i : i + page_size]
