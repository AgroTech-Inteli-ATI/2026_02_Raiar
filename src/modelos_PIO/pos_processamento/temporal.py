"""Estabilização temporal da contagem (porte do filtro de Kalman 1D da RaiarNet)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Kalman1D:
    """Nível constante: x_k = x_{k-1} + w, z_k = x_k + v (mesmos q, r da RaiarNet)."""

    q: float = 0.5
    r: float = 4.0
    x: float | None = None
    p: float = 10.0

    def update(self, z: float) -> float:
        if self.x is None:
            self.x = z
            return z
        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (z - self.x)
        self.p *= 1 - k
        return self.x


def suavizar_serie(valores, q: float = 0.5, r: float = 4.0) -> list[float]:
    f = Kalman1D(q=q, r=r)
    return [f.update(float(v)) for v in valores]
