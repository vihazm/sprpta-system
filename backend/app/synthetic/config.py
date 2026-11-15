"""The simulation assumptions, read from synthetic_config.toml (every value can be reviewed and changed there)."""

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "synthetic_config.toml"
SCALES = ("small", "medium", "large")


@dataclass
class Config:
    raw: dict[str, Any]
    scale: str

    @property
    def start(self) -> date:
        return date.fromisoformat(self.raw["general"]["start"])

    @property
    def end(self) -> date:
        return date.fromisoformat(self.raw["general"]["end"])

    @property
    def seed(self) -> int:
        return int(self.raw["general"]["seed"])

    @property
    def batch_name(self) -> str:
        return f'{self.raw["general"]["batch_name"]}-{self.scale}'

    def section(self, name: str) -> dict[str, Any]:
        return self.raw[name]

    @property
    def scale_settings(self) -> dict[str, Any]:
        return self.raw["scales"][self.scale]

    def window(self) -> tuple[date, date]:
        """The first and last day simulated at this scale: the most recent N days of the period."""
        from datetime import timedelta

        days = int(self.scale_settings["days"])
        return max(self.start, self.end - timedelta(days=days - 1)), self.end


def load(scale: str = "small", path: Path | str | None = None, overrides: dict[str, dict[str, Any]] | None = None) -> Config:
    if scale not in SCALES:
        raise SystemExit(f"Unknown scale {scale!r}. Choose one of: {', '.join(SCALES)}.")
    with open(path or DEFAULT_PATH, "rb") as handle:
        raw = tomllib.load(handle)
    for section, values in (overrides or {}).items():
        raw.setdefault(section, {}).update(values)
    return Config(raw=raw, scale=scale)
