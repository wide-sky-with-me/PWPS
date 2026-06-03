"""Calculator tool — performs welding-related calculations."""

from __future__ import annotations

import json
import re

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class HeatInputCalculationInput(BaseModel):
    """Input for heat input calculation."""

    current: str = Field(description="Welding current with unit, e.g. '180A' or '180'")
    voltage: str = Field(description="Welding voltage with unit, e.g. '24V' or '24'")
    travel_speed: str = Field(description="Travel speed with unit, e.g. '30cm/min' or '30'")


class HeatInputCalculator(BaseTool):
    """Calculate welding heat input from current, voltage, and travel speed.

    Formula: heat_input (kJ/mm) = current(A) × voltage(V) × 60 / (speed(cm/min) × 1000)
    """

    name: str = "calculate_heat_input"
    description: str = (
        "Calculate welding heat input in kJ/mm. "
        "Input: current (A), voltage (V), travel speed (cm/min). "
        "Returns: calculated heat input value."
    )
    args_schema: type[BaseModel] = HeatInputCalculationInput

    async def _arun(self, current: str, voltage: str, travel_speed: str) -> str:
        """Calculate heat input."""
        try:
            c = _extract_number(current)
            v = _extract_number(voltage)
            s = _extract_number(travel_speed)

            if s <= 0:
                return json.dumps({"error": "Travel speed must be positive."})

            heat_input = (c * v * 60) / (s * 1000)
            return json.dumps({
                "heat_input_kj_mm": round(heat_input, 2),
                "formula": f"({c}A × {v}V × 60) / ({s}cm/min × 1000) = {heat_input:.2f} kJ/mm",
                "inputs": {"current_A": c, "voltage_V": v, "speed_cm_min": s},
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _run(self, current: str, voltage: str, travel_speed: str) -> str:
        raise NotImplementedError("Use async version")


def _extract_number(value: str) -> float:
    """Extract a numeric value from a string like '180A' or '24V'."""
    m = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if not m:
        raise ValueError(f"Cannot extract number from '{value}'")
    return float(m.group(1))
