"""ChartBuilder — 7 chart-type dispatch + axis-mapping validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

ChartType = Literal["line", "bar", "pie", "scatter", "heatmap", "box", "area"]
_VALID: tuple[ChartType, ...] = ("line", "bar", "pie", "scatter", "heatmap", "box", "area")

MAX_ROWS = 100_000


@dataclass(frozen=True, slots=True)
class AxisMapping:
    x: str | None = None
    y: str | list[str] | None = None
    color: str | None = None
    size: str | None = None


@dataclass(frozen=True, slots=True)
class ChartSpec:
    engine: Literal["plotly"]
    spec: dict[str, Any]


def build(
    rows: list[dict[str, Any]],
    chart_type: ChartType,
    mapping: AxisMapping,
) -> Result[ChartSpec, DomainError]:
    if chart_type not in _VALID:
        return Err(DomainError.VALIDATION)
    if len(rows) > MAX_ROWS:
        return Err(DomainError.VALIDATION)
    if chart_type in ("line", "bar", "scatter", "area", "box"):
        if mapping.x is None or mapping.y is None:
            return Err(DomainError.VALIDATION)
    if chart_type == "pie" and mapping.y is None:
        return Err(DomainError.VALIDATION)
    return Ok(ChartSpec(engine="plotly", spec=_render(chart_type, rows, mapping)))


def _render(chart_type: ChartType, rows: list[dict[str, Any]], mapping: AxisMapping) -> dict[str, Any]:
    if chart_type in ("line", "scatter"):
        return {
            "type": chart_type,
            "data": [
                {
                    "x": [r.get(mapping.x) for r in rows],
                    "y": [r.get(mapping.y if isinstance(mapping.y, str) else (mapping.y or ["y"])[0]) for r in rows],
                    "mode": "lines" if chart_type == "line" else "markers",
                }
            ],
        }
    if chart_type == "bar":
        return {
            "type": "bar",
            "x": [r.get(mapping.x) for r in rows],
            "y": [r.get(mapping.y if isinstance(mapping.y, str) else (mapping.y or ["y"])[0]) for r in rows],
        }
    if chart_type == "pie":
        y_key = mapping.y if isinstance(mapping.y, str) else (mapping.y or ["y"])[0]
        return {
            "type": "pie",
            "labels": [r.get(mapping.x) for r in rows],
            "values": [r.get(y_key) for r in rows],
        }
    if chart_type == "area":
        return {"type": "area", "x": [r.get(mapping.x) for r in rows], "y": [r.get(mapping.y) for r in rows]}
    if chart_type == "box":
        return {"type": "box", "y": [r.get(mapping.y) for r in rows]}
    # heatmap
    return {"type": "heatmap", "z": [[r.get(mapping.y) for r in rows]]}
