"""Водяной знак на фото объявления перед публикацией в канал.

Текст-знак (название агентства) ставится в правый нижний угол с обводкой для
читаемости на любом фоне. Всё завёрнуто в try/except: при любой ошибке
(нет сети/шрифта/Pillow) возвращается исходный file_id — публикация не ломается.
"""
from __future__ import annotations

import io
import logging

from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.config import WATERMARK_TEXT

logger = logging.getLogger(__name__)

# Шрифты с поддержкой кириллицы и узбекской латиницы (DejaVu ставится в Docker).
_FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _load_font(size: int):
    from PIL import ImageFont

    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1 (может не знать кириллицу)
    except TypeError:
        return ImageFont.load_default()


def stamp(image_bytes: bytes, text: str) -> bytes:
    """Наложить текстовый водяной знак и вернуть JPEG-байты."""
    from PIL import Image, ImageDraw

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = img.size
    draw = ImageDraw.Draw(img)

    size = max(16, width // 22)
    font = _load_font(size)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = max(8, width // 60)
    x, y = width - tw - pad, height - th - pad

    draw.text(
        (x, y), text, font=font,
        fill=(255, 255, 255), stroke_width=max(1, size // 12), stroke_fill=(0, 0, 0),
    )
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


async def watermark_photos(bot: Bot, file_ids: list[str]) -> list:
    """file_id → BufferedInputFile с водяным знаком. При сбое — исходный file_id."""
    if not WATERMARK_TEXT:
        return list(file_ids)
    result: list = []
    for fid in file_ids:
        try:
            buf = io.BytesIO()
            await bot.download(fid, destination=buf)
            data = stamp(buf.getvalue(), WATERMARK_TEXT)
            result.append(BufferedInputFile(data, filename="photo.jpg"))
        except Exception:  # noqa: BLE001 - любой сбой → публикуем оригинал
            logger.debug("Водяной знак пропущен для %s (откат к оригиналу)", fid)
            result.append(fid)
    return result
