"""Small standards-aware Touchstone v1 reader.

The parser supports RI, MA, and DB data for arbitrary N-port files. It follows
the Touchstone ordering S11, S21, ... SN1, S12, S22, ... SNN and exposes an
explicit ``s(i, j)`` accessor to avoid ambiguous hard-coded column indexes.
"""

from __future__ import annotations

import cmath
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


_PORTS_RE = re.compile(r"\.s(\d+)p$", re.IGNORECASE)
_FREQ_SCALE = {
    "HZ": 1.0,
    "KHZ": 1e3,
    "MHZ": 1e6,
    "GHZ": 1e9,
}


@dataclass(frozen=True)
class TouchstoneData:
    frequency_hz: Tuple[float, ...]
    ports: int
    reference_ohm: float
    parameters: Dict[Tuple[int, int], Tuple[complex, ...]]

    def s(self, output_port: int, input_port: int) -> Tuple[complex, ...]:
        """Return S(output_port, input_port), using one-based port numbers."""
        try:
            return self.parameters[(output_port, input_port)]
        except KeyError as exc:
            raise ValueError(
                f"Invalid S-parameter S({output_port},{input_port}) for {self.ports}-port data"
            ) from exc

    def db(self, output_port: int, input_port: int, floor_db: float = -300.0) -> Tuple[float, ...]:
        values = []
        for value in self.s(output_port, input_port):
            magnitude = abs(value)
            values.append(20.0 * math.log10(magnitude) if magnitude > 0 else floor_db)
        return tuple(values)


def _ports_from_path(path: Path) -> int:
    match = _PORTS_RE.search(path.name)
    if not match:
        raise ValueError(f"Cannot infer port count from Touchstone suffix: {path.name}")
    ports = int(match.group(1))
    if ports <= 0:
        raise ValueError("Touchstone port count must be positive")
    return ports


def _to_complex(first: float, second: float, data_format: str) -> complex:
    if data_format == "RI":
        return complex(first, second)
    if data_format == "MA":
        return cmath.rect(first, math.radians(second))
    if data_format == "DB":
        return cmath.rect(10.0 ** (first / 20.0), math.radians(second))
    raise ValueError(f"Unsupported Touchstone data format: {data_format}")


def _records(tokens: Sequence[float], values_per_record: int) -> Iterable[Sequence[float]]:
    if len(tokens) % values_per_record != 0:
        raise ValueError(
            f"Incomplete Touchstone record: {len(tokens)} numeric values cannot be divided "
            f"into records of {values_per_record}"
        )
    for start in range(0, len(tokens), values_per_record):
        yield tokens[start : start + values_per_record]


def read_touchstone(path: str | Path) -> TouchstoneData:
    file_path = Path(path)
    ports = _ports_from_path(file_path)
    frequency_unit = "GHZ"
    data_format = "MA"
    reference_ohm = 50.0
    numeric_tokens: List[float] = []

    for raw_line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.split("!", 1)[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            parts = line[1:].upper().split()
            if parts:
                frequency_unit = parts[0]
            if "RI" in parts:
                data_format = "RI"
            elif "DB" in parts:
                data_format = "DB"
            elif "MA" in parts:
                data_format = "MA"
            if "R" in parts:
                index = parts.index("R")
                if index + 1 >= len(parts):
                    raise ValueError("Touchstone option line contains R without a value")
                reference_ohm = float(parts[index + 1])
            continue
        numeric_tokens.extend(float(token) for token in line.split())

    if frequency_unit not in _FREQ_SCALE:
        raise ValueError(f"Unsupported Touchstone frequency unit: {frequency_unit}")

    values_per_record = 1 + 2 * ports * ports
    frequencies: List[float] = []
    series: Dict[Tuple[int, int], List[complex]] = {
        (output_port, input_port): []
        for input_port in range(1, ports + 1)
        for output_port in range(1, ports + 1)
    }

    for record in _records(numeric_tokens, values_per_record):
        frequencies.append(record[0] * _FREQ_SCALE[frequency_unit])
        cursor = 1
        for input_port in range(1, ports + 1):
            for output_port in range(1, ports + 1):
                series[(output_port, input_port)].append(
                    _to_complex(record[cursor], record[cursor + 1], data_format)
                )
                cursor += 2

    if not frequencies:
        raise ValueError(f"No Touchstone samples found in {file_path}")

    return TouchstoneData(
        frequency_hz=tuple(frequencies),
        ports=ports,
        reference_ohm=reference_ohm,
        parameters={key: tuple(values) for key, values in series.items()},
    )
