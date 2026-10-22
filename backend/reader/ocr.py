"""OCR z RapidOCR (modeli PP-OCR v ONNX Runtime): slika → škatle z besedilom."""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

from .errors import ReceiptError

# Večje slike OCR le upočasnijo, natančnosti pa ne izboljšajo.
MAX_SIDE = 1600

_engine = None


@dataclass
class Box:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    score: float

    @property
    def y_mid(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


def _get_engine():
    # Modeli se naložijo ob prvem klicu (~1 s), nato ostanejo v pomnilniku.
    global _engine
    if _engine is None:
        from rapidocr import RapidOCR

        _engine = RapidOCR()
    return _engine


def prepare_image(data: bytes) -> np.ndarray:
    """Poravna po EXIF, pretvori v RGB in pomanjša na MAX_SIDE."""
    try:
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except Exception as e:
        raise ReceiptError("Slike ni mogoče odpreti. Naloži JPG, PNG ali WEBP.") from e
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    return np.asarray(image)


def read_boxes(data: bytes) -> list[Box]:
    result = _get_engine()(prepare_image(data))
    if result.boxes is None or result.txts is None:
        return []
    boxes = []
    for corners, text, score in zip(result.boxes, result.txts, result.scores):
        xs = [float(p[0]) for p in corners]
        ys = [float(p[1]) for p in corners]
        boxes.append(Box(min(xs), min(ys), max(xs), max(ys), text, float(score)))
    return boxes
