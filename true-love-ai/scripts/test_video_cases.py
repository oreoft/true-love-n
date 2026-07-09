#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时测试脚本：跑一遍 VideoService 的所有场景（文生视频/图生视频 x 默认模型/降级模型 + 完整流程）。
用法（在 true-love-ai 目录下执行，需要 config.yaml / config-dev.yaml 里的 litellm 配置有效）：
    uv run python scripts/test_video_cases.py
跑完可以删掉这个脚本。
"""
import asyncio
import base64
import io
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import Image, ImageDraw  # noqa: E402

from true_love_ai.core.model_registry import get_model_registry  # noqa: E402
from true_love_ai.llm.llm_bootstrap import init_llm  # noqa: E402
from true_love_ai.services.video_service import VideoService  # noqa: E402

TEXT_PROMPT = "一只橘猫在阳光下弹钢琴"


def make_test_image_b64() -> str:
    """生成一张 512x512 的测试图（纯色+文字），比 1x1 像素更接近真实使用场景"""
    img = Image.new("RGB", (512, 512), color=(255, 200, 120))
    draw = ImageDraw.Draw(img)
    draw.ellipse((150, 150, 362, 362), fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


async def run_case(name: str, coro):
    print(f"\n{'=' * 60}\n[开始] {name}\n{'=' * 60}")
    start = time.time()
    try:
        result = await coro
        cost = time.time() - start
        print(f"[成功] {name} 耗时 {cost:.1f}s")
        print(f"  video_id={result.video_id}")
        print(f"  prompt={result.prompt[:80]}...")
        return True
    except Exception as e:
        cost = time.time() - start
        print(f"[失败] {name} 耗时 {cost:.1f}s")
        print(f"  错误: {e}")
        traceback.print_exc()
        return False


async def main():
    init_llm()
    registry = get_model_registry()
    default_model = registry.get("video", "default")
    fallback_model = registry.get("video", "fallback")
    print(f"当前 video 模型配置: default={default_model} fallback={fallback_model}")

    svc = VideoService()
    img_b64 = make_test_image_b64()

    results = {}

    # 1. 纯文本 + 默认模型（不经过 prompt 翻译，直接测 _generate_by_model）
    results["text + default model"] = await run_case(
        f"文生视频 - 默认模型({default_model})",
        svc._generate_by_model(TEXT_PROMPT, default_model, None),
    )

    # 2. 纯文本 + 备用模型
    if fallback_model:
        results["text + fallback model"] = await run_case(
            f"文生视频 - 备用模型({fallback_model})",
            svc._generate_by_model(TEXT_PROMPT, fallback_model, None),
        )

    # 3. 图片 + 默认模型（验证 _detect_image 修复）
    results["image + default model"] = await run_case(
        f"图生视频 - 默认模型({default_model})",
        svc._generate_by_model(TEXT_PROMPT, default_model, [img_b64]),
    )

    # 4. 图片 + 备用模型
    if fallback_model:
        results["image + fallback model"] = await run_case(
            f"图生视频 - 备用模型({fallback_model})",
            svc._generate_by_model(TEXT_PROMPT, fallback_model, [img_b64]),
        )

    # 5. 完整流程（含 prompt 翻译 + 自动降级）- 纯文本
    results["generate_video() text full flow"] = await run_case(
        "完整流程 generate_video() - 纯文本",
        svc.generate_video(TEXT_PROMPT),
    )

    # 6. 完整流程（含 prompt 翻译 + 自动降级）- 图生视频
    results["generate_video() image full flow"] = await run_case(
        "完整流程 generate_video() - 图生视频",
        svc.generate_video(TEXT_PROMPT, [img_b64]),
    )

    print(f"\n{'=' * 60}\n汇总\n{'=' * 60}")
    for name, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {name}")


if __name__ == "__main__":
    asyncio.run(main())