#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""语音服务：文本转语音（通过 LiteLLM proxy HTTP API）"""
import io
import logging
import uuid
import wave
from pathlib import Path

import lameenc
from true_love_common.http.client import HttpResult, async_post

from true_love_ai.core.config import get_config
from true_love_ai.core.model_registry import get_model_registry
from true_love_ai.models.response import AudioResponse

LOG = logging.getLogger(__name__)

GEN_AUDIO_DIR = Path("gen_audio")
GEN_AUDIO_DIR.mkdir(exist_ok=True)


class AudioService:

    def __init__(self):
        cfg = get_config()
        self.registry = get_model_registry()
        self.base_url = cfg.platform_key.litellm_base_url.rstrip("/")
        self.api_key = cfg.platform_key.litellm_api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def text_to_speech(self, text: str, voice: str = "Kore") -> AudioResponse:
        default_model = self.registry.get("tts", "default")
        fallback_model = self.registry.get("tts", "fallback")

        try:
            return await self._generate_by_model(text, default_model, voice)
        except Exception as e:
            if fallback_model:
                LOG.warning("主力语音合成失败，降级备用模型 %s: %s", fallback_model, e)
                return await self._generate_by_model(text, fallback_model, voice)
            raise

    async def _generate_by_model(self, text: str, model: str, voice: str) -> AudioResponse:
        LOG.info("生成语音: model=%s voice=%s", model, voice)
        body = {"model": model, "input": text, "voice": voice}

        resp = await async_post(f"{self.base_url}/v1/audio/speech", headers=self._headers(), json=body, timeout=60.0)
        self._raise_for_audio_error(resp)

        mp3_bytes, duration = self._wav_to_mp3(resp.content)

        aid = str(uuid.uuid4())
        audio_path = GEN_AUDIO_DIR / f"{aid}.mp3"
        audio_path.write_bytes(mp3_bytes)
        LOG.info("语音完成: %s (%.2fKB, %.1fs)", audio_path, len(mp3_bytes) / 1024, duration)
        return AudioResponse(text=text, audio_id=aid, duration_seconds=duration)

    @staticmethod
    def _wav_to_mp3(data: bytes) -> tuple[bytes, float]:
        """把 TTS 返回的 wav（pcm16）编码为 mp3；纯 Python 依赖（lameenc 自带 libmp3lame），无需系统装 ffmpeg"""
        with wave.open(io.BytesIO(data)) as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
            duration = round(wf.getnframes() / float(sample_rate), 2)

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(64)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(channels)
        encoder.set_quality(2)
        mp3_bytes = encoder.encode(pcm) + encoder.flush()
        return mp3_bytes, duration

    @staticmethod
    def _raise_for_audio_error(resp: HttpResult) -> None:
        if resp.status_code == 429:
            raise ValueError("呜呜~语音酱今天太累了，等一会再来找我玩吧~")
        if resp.status_code >= 400:
            err = resp.text.lower()
            if any(k in err for k in ["content_policy", "safety", "filtered", "blocked"]):
                raise ValueError("生成失败啦! 内容太不堪入目了吧~")
            raise ValueError(f"语音接口错误 {resp.status_code}: {resp.text[:200]}")
