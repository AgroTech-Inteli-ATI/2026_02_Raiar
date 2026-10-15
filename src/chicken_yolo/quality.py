"""Triagem técnica; não substitui revisão da visibilidade das aves e níveis."""

from .config import QualityConfig
from .domain import Frame


def assess_quality(frame: Frame, config: QualityConfig) -> tuple[str | None, dict]:
    if frame.error or frame.image is None:
        return frame.error or "Imagem não decodificada.", {}
    if frame.manual_quality == "nao_avaliavel":
        return frame.extra.get("motivo_qualidade", "Imagem rejeitada na revisão manual."), {}
    import cv2

    height, width = frame.image.shape[:2]
    if width < config.min_width or height < config.min_height:
        return "Resolução abaixo do mínimo configurado.", {"width": width, "height": height}
    gray = cv2.cvtColor(frame.image, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    metrics = {"brightness": brightness, "blur_score": blur}
    if brightness < config.min_brightness or brightness > config.max_brightness:
        return "Brilho fora da faixa configurada.", metrics
    if config.min_blur_score is not None and blur < config.min_blur_score:
        return "Desfoque acima do limite configurado.", metrics
    return None, metrics
