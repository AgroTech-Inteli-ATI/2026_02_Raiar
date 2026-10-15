"""Zonas calibradas com coordenadas normalizadas e fronteiras indeterminadas."""

import math
from dataclasses import dataclass
from pathlib import Path

from .config import fingerprint, load_yaml

EPSILON = 1e-9


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(point, a, b):
    return abs(_cross(a, b, point)) <= EPSILON and all(
        min(a[i], b[i]) - EPSILON <= point[i] <= max(a[i], b[i]) + EPSILON for i in (0, 1)
    )


def _intersects(a, b, c, d):
    return (_cross(a, b, c) * _cross(a, b, d) < 0 and _cross(c, d, a) * _cross(c, d, b) < 0) or any(
        (_on_segment(c, a, b), _on_segment(d, a, b), _on_segment(a, c, d), _on_segment(b, c, d))
    )


def point_location(point: tuple[float, float], polygon: tuple) -> int:
    """Retorna -1 fora, 0 na fronteira e 1 dentro do polígono."""
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if _on_segment(point, a, b):
            return 0
        if (a[1] > point[1]) != (b[1] > point[1]):
            x = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if point[0] < x:
                inside = not inside
    return 1 if inside else -1


@dataclass(frozen=True)
class Zone:
    id: str
    polygon: tuple[tuple[float, float], ...]

    def __post_init__(self):
        if not self.id or len(self.polygon) < 3 or len(set(self.polygon)) != len(self.polygon):
            raise ValueError("Zona precisa de ID e pelo menos três vértices distintos.")
        if any(
            len(p) != 2 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in p)
            for p in self.polygon
        ):
            raise ValueError("Coordenadas de zona devem estar normalizadas entre 0 e 1.")
        edges = list(zip(self.polygon, self.polygon[1:] + self.polygon[:1], strict=True))
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in edges)) / 2
        if area <= EPSILON:
            raise ValueError("Polígono de zona não pode ter área zero.")
        for i, (a, b) in enumerate(edges):
            for j, (c, d) in enumerate(edges):
                if j > i + 1 and not (i == 0 and j == len(edges) - 1):
                    if _intersects(a, b, c, d):
                        raise ValueError("Polígono de zona não pode se cruzar.")


@dataclass(frozen=True)
class ZoneConfig:
    camera_id: str
    version: str
    rule_version: str
    reference_size: tuple[int, int]
    zones: tuple[Zone, ...]
    sha256: str
    aspect_ratio_tolerance: float = 0.02

    def check_frame(self, width: int, height: int, camera_id: str | None) -> str | None:
        if camera_id != self.camera_id:
            return "A câmera do quadro não corresponde à calibração das zonas."
        reference_ratio = self.reference_size[0] / self.reference_size[1]
        if abs((width / height) / reference_ratio - 1) > self.aspect_ratio_tolerance:
            return "Proporção da imagem diferente da referência das zonas."
        return None

    def assign(self, bbox, width: int, height: int) -> tuple[str | None, str | None]:
        point = ((bbox[0] + bbox[2]) / (2 * width), bbox[3] / height)
        locations = [(zone.id, point_location(point, zone.polygon)) for zone in self.zones]
        if any(location == 0 for _, location in locations):
            return None, "fronteira"
        matches = [zone_id for zone_id, location in locations if location == 1]
        if len(matches) == 1:
            return matches[0], None
        return None, "zonas_sobrepostas" if matches else "fora_das_zonas"


def load_zones(path: Path) -> ZoneConfig:
    raw = load_yaml(path)
    if raw.get("calibrated") is not True:
        raise ValueError("Zonas são um exemplo ou ainda não foram calibradas.")
    zones = tuple(Zone(z["id"], tuple(tuple(p) for p in z["polygon"])) for z in raw["zones"])
    size = tuple(raw["reference_size"])
    if len(size) != 2 or min(size) <= 0 or not zones:
        raise ValueError("Informe dimensões positivas e zonas calibradas.")
    if len({zone.id for zone in zones}) != len(zones):
        raise ValueError("IDs de zonas devem ser únicos.")
    tolerance = float(raw.get("aspect_ratio_tolerance", 0.02))
    if not 0 <= tolerance <= 0.2:
        raise ValueError("Tolerância da proporção deve estar entre 0 e 0,2.")
    return ZoneConfig(
        raw["camera_id"],
        raw["version"],
        raw["rule_version"],
        size,
        zones,
        fingerprint(raw),
        tolerance,
    )
