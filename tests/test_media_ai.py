"""Тесты Vision (скрины) и транскрипции (голос): выключенное состояние и
рабочий путь с подставным клиентом (без сети)."""
from types import SimpleNamespace

from bot.services import transcribe, vision


# --- Vision -----------------------------------------------------------------
async def test_vision_disabled_returns_none():
    svc = vision.VisionService()
    svc._client = None  # без ключа
    assert svc.is_enabled() is False
    assert await svc.extract_listing_text(b"\x89PNG...") is None


async def test_vision_extracts_text_with_mock():
    svc = vision.VisionService()

    class FakeCompletions:
        async def create(self, **kwargs):
            # проверим, что картинка ушла как image_url
            content = kwargs["messages"][0]["content"]
            assert any(part["type"] == "image_url" for part in content)
            msg = SimpleNamespace(content="2 хона ижара Киргули 450 минг")
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    svc._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    assert svc.is_enabled() is True
    text = await svc.extract_listing_text(b"imgbytes")
    assert "Киргули" in text


async def test_vision_empty_answer_is_none():
    svc = vision.VisionService()

    class FakeCompletions:
        async def create(self, **kwargs):
            msg = SimpleNamespace(content="   ")
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    svc._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    assert await svc.extract_listing_text(b"x") is None


# --- Transcription ----------------------------------------------------------
async def test_transcribe_disabled_returns_none():
    svc = transcribe.TranscribeService()
    svc._client = None
    assert svc.is_enabled() is False
    assert await svc.transcribe(b"ogg") is None


async def test_transcribe_with_mock():
    svc = transcribe.TranscribeService()

    class FakeTranscriptions:
        async def create(self, **kwargs):
            return SimpleNamespace(text="сотилади ховли участка")

    svc._client = SimpleNamespace(audio=SimpleNamespace(transcriptions=FakeTranscriptions()))
    assert svc.is_enabled() is True
    text = await svc.transcribe(b"audio")
    assert "ховли" in text
