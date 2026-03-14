"""
視覺回歸與設計合規 (Visual Regression & Design Compliance)

利用 Playwright 截取實際渲染頁面，與設計稿參考圖進行像素/結構比對。
比對失敗時可將差異描述送入 RootCauseAnalyzer 進行根因分析。
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# 預設可接受像素差異比例（0.0 = 完全一致）
DEFAULT_PIXEL_DIFF_THRESHOLD = 0.01


@dataclass
class VisualComplianceResult:
    """視覺合規比對結果"""
    passed: bool
    diff_ratio: float
    reference_path: Optional[str] = None
    actual_path: Optional[str] = None
    diff_image_path: Optional[str] = None
    viewport: Dict[str, int] = field(default_factory=dict)
    message: str = ""


async def _screenshot_url(
    url: str,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    wait_until: str = "networkidle",
    timeout_ms: int = 30000,
) -> bytes:
    """使用 Playwright 截取指定 URL 的畫面。"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "playwright 為必要依賴。請執行: pip install playwright && playwright install chromium"
        )
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height}
        )
        page = await context.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        await page.wait_for_timeout(500)
        screenshot_bytes = await page.screenshot(full_page=False)
        await browser.close()
    return screenshot_bytes


def _load_image(path_or_bytes: str | bytes) -> "Image.Image":
    """載入圖片為 PIL Image。"""
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("Pillow 為視覺比對必要依賴。請執行: pip install Pillow")
    if isinstance(path_or_bytes, bytes):
        return Image.open(io.BytesIO(path_or_bytes)).convert("RGB")
    return Image.open(path_or_bytes).convert("RGB")


def _pixel_diff_ratio(img_ref: "Image.Image", img_actual: "Image.Image") -> tuple[float, Optional["Image.Image"]]:
    """
    計算兩張圖的像素差異比例，並產生差異圖（可選）。
    回傳 (差異比例 0~1, 差異圖 PIL Image 或 None)。
    """
    from PIL import ImageChops, Image
    w1, h1 = img_ref.size
    w2, h2 = img_actual.size
    if (w1, h1) != (w2, h2):
        img_actual = img_actual.resize((w1, h1), getattr(Image, "LANCZOS", Image.BICUBIC))
    diff = ImageChops.difference(img_ref, img_actual)
    diff_gray = diff.convert("L")
    total = w1 * h1
    if total == 0:
        return 0.0, diff.convert("RGB")
    threshold = 30
    diff_pixels = sum(1 for _ in diff_gray.getdata() if _ > threshold)
    ratio = diff_pixels / total
    diff_vis = diff.convert("RGB")
    return ratio, diff_vis


async def run_visual_compliance(
    reference_image_path: str,
    live_url: str,
    output_dir: Optional[str] = None,
    pixel_diff_threshold: float = DEFAULT_PIXEL_DIFF_THRESHOLD,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    on_failure_analyze: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> VisualComplianceResult:
    """
    執行視覺合規檢查：比對參考圖與實際渲染頁面。

    - reference_image_path: 設計稿或基準截圖路徑（PNG/JPEG）
    - live_url: 實際網頁 URL（由 Playwright 開啟並截圖）
    - output_dir: 存放實際截圖與差異圖的目錄；為 None 則不寫入
    - pixel_diff_threshold: 可接受之像素差異比例上限（0.01 = 1%）
    - on_failure_analyze: 比對失敗時呼叫，傳入 error 字典（含 message、diff_ratio、paths），
                          可轉交 RootCauseAnalyzer.analyze(error, [], {})
    """
    if not os.path.isfile(reference_image_path):
        return VisualComplianceResult(
            passed=False,
            diff_ratio=1.0,
            message=f"參考圖不存在: {reference_image_path}",
        )
    ref_img = _load_image(reference_image_path)
    actual_bytes = await _screenshot_url(
        live_url,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )
    actual_img = _load_image(actual_bytes)
    diff_ratio, diff_image = _pixel_diff_ratio(ref_img, actual_img)
    passed = diff_ratio <= pixel_diff_threshold

    actual_path: Optional[str] = None
    diff_image_path: Optional[str] = None
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        actual_path = os.path.join(output_dir, "actual-screenshot.png")
        with open(actual_path, "wb") as f:
            f.write(actual_bytes)
        if diff_image and not passed:
            diff_image_path = os.path.join(output_dir, "visual-diff.png")
            diff_image.save(diff_image_path)

    result = VisualComplianceResult(
        passed=passed,
        diff_ratio=diff_ratio,
        reference_path=reference_image_path,
        actual_path=actual_path,
        diff_image_path=diff_image_path,
        viewport={"width": viewport_width, "height": viewport_height},
        message="通過" if passed else f"像素差異 {diff_ratio:.2%} 超過閾值 {pixel_diff_threshold:.2%}",
    )

    if not passed and on_failure_analyze:
        error_payload = {
            "message": (
                f"Visual regression: pixel diff ratio {diff_ratio:.2%} exceeds threshold {pixel_diff_threshold:.2%}. "
                f"Reference: {reference_image_path}, Actual: {actual_path or 'in-memory'}, Diff: {diff_image_path or 'N/A'}"
            ),
            "type": "visual_regression",
            "diff_ratio": diff_ratio,
            "reference_path": reference_image_path,
            "actual_path": actual_path,
            "diff_image_path": diff_image_path,
        }
        try:
            if asyncio.iscoroutinefunction(on_failure_analyze):
                await on_failure_analyze(error_payload)
            else:
                on_failure_analyze(error_payload)
        except Exception as e:
            logger.warning("視覺失敗回調（如 RootCauseAnalyzer）執行錯誤: %s", e)

    return result


def run_visual_compliance_sync(
    reference_image_path: str,
    live_url: str,
    **kwargs: Any,
) -> VisualComplianceResult:
    """同步包裝。"""
    return asyncio.run(run_visual_compliance(reference_image_path, live_url, **kwargs))
