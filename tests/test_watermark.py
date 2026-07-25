"""Тесты водяного знака: ядро на Pillow + graceful-fallback без сети."""
import io

import pytest

from bot.services import watermark  # PIL импортируется внутри функций — импорт безопасен


def _sample_png() -> bytes:
    Image = pytest.importorskip("PIL.Image")
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (120, 120, 120)).save(buf, format="PNG")
    return buf.getvalue()


def test_stamp_returns_valid_jpeg_and_changes_image():
    Image = pytest.importorskip("PIL.Image")  # пропустить, если Pillow не установлен
    src = _sample_png()
    out = watermark.stamp(src, "Фарғона Уйлари")
    assert out and out != src
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"
    assert img.size == (800, 600)  # размер сохранён


async def test_watermark_photos_falls_back_without_download():
    """У «бота» нет download → возвращаем исходные file_id, не роняя публикацию."""
    class NoDownloadBot:
        pass

    result = await watermark.watermark_photos(NoDownloadBot(), ["f1", "f2"])
    assert result == ["f1", "f2"]
