"""ChartBuilder — 7가지 차트 유형 디스패치 + 축 매핑(axis-mapping) 검증.

행 데이터와 축 매핑을 받아 프런트엔드 plotly가 그릴 수 있는 차트 사양(spec)을
만든다. 검증을 먼저 통과시킨 뒤에만 렌더로 넘겨, 유형별로 필요한 축이 빠진 채
잘못된 사양이 만들어지는 것을 막는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

# 지원 차트 유형. _VALID는 입력 검증용 화이트리스트(허용 목록)다.
ChartType = Literal["line", "bar", "pie", "scatter", "heatmap", "box", "area"]
_VALID: tuple[ChartType, ...] = ("line", "bar", "pie", "scatter", "heatmap", "box", "area")

# 브라우저 렌더 부담을 막는 행 수 상한. 초과하면 차트를 만들지 않고 거부한다.
MAX_ROWS = 100_000


@dataclass(frozen=True, slots=True)
class AxisMapping:
    # 컬럼명 → 축 역할 매핑. y는 다중 시리즈를 위해 리스트도 허용한다.
    x: str | None = None
    y: str | list[str] | None = None
    color: str | None = None
    size: str | None = None


@dataclass(frozen=True, slots=True)
class ChartSpec:
    # 프런트엔드에 넘기는 렌더 사양. 엔진은 현재 plotly로 고정.
    engine: Literal["plotly"]
    spec: dict[str, Any]


def build(
    rows: list[dict[str, Any]],
    chart_type: ChartType,
    mapping: AxisMapping,
) -> Result[ChartSpec, DomainError]:
    # 렌더 전 게이트: 유형·행 수·필수 축을 모두 통과해야만 사양을 만든다.
    if chart_type not in _VALID:
        return Err(DomainError.VALIDATION)
    if len(rows) > MAX_ROWS:
        return Err(DomainError.VALIDATION)
    # 직교 좌표계 차트는 x·y 둘 다 있어야 의미가 있다.
    if chart_type in ("line", "bar", "scatter", "area", "box"):
        if mapping.x is None or mapping.y is None:
            return Err(DomainError.VALIDATION)
    # 파이는 값(y)이 핵심 — x(라벨)는 없어도 되지만 y는 필수.
    if chart_type == "pie" and mapping.y is None:
        return Err(DomainError.VALIDATION)
    return Ok(ChartSpec(engine="plotly", spec=_render(chart_type, rows, mapping)))


def _render(chart_type: ChartType, rows: list[dict[str, Any]], mapping: AxisMapping) -> dict[str, Any]:
    # 유형별로 행을 축 배열로 펼친다. build()에서 이미 검증을 통과했다는
    # 전제하에 동작하므로 여기서는 형식 변환에만 집중한다.
    # y가 리스트로 들어오면 첫 시리즈만 쓴다(단일 시리즈 차트 기준).
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
    # 남은 유형은 heatmap. z는 2차원 행렬이어야 하므로 한 줄로 감싼다.
    return {"type": "heatmap", "z": [[r.get(mapping.y) for r in rows]]}
