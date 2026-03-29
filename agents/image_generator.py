import base64
import os
from datetime import datetime

import requests

from config import BYTEZ_API_KEY, BYTEZ_IMAGE_MODEL, OUTPUT_DIR, STABILITY_API_KEY

try:
    from bytez import Bytez
except ImportError:  # pragma: no cover - optional dependency at runtime
    Bytez = None


class ImageGenerator:
    """
    Generates post images.

    Preferred provider:
    - Bytez model: stabilityai/stable-diffusion-xl-base-1.0

    Fallback:
    - Stability AI REST API
    """

    API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    FORMATS = {
        "blog": {"width": 1344, "height": 768, "label": "Blog Hero (~16:9)"},
        "instagram": {"width": 1024, "height": 1024, "label": "Instagram (1:1)"},
        "linkedin": {"width": 1536, "height": 640, "label": "LinkedIn (wide landscape)"},
    }

    def __init__(self):
        self.stability_api_key = STABILITY_API_KEY
        self.bytez_api_key = BYTEZ_API_KEY
        self.bytez_model_name = BYTEZ_IMAGE_MODEL
        self.img_dir = os.path.join(OUTPUT_DIR, "images")
        os.makedirs(self.img_dir, exist_ok=True)

        self.bytez_client = None
        if self.bytez_api_key and Bytez is not None:
            try:
                self.bytez_client = Bytez(self.bytez_api_key)
            except Exception as exc:
                print(f"[ImageGenerator] Failed to initialize Bytez client: {exc}")

    def generate(
        self,
        title: str,
        topic: str,
        mode: str,
        formats: list = None,
        key_fact: str = "",
        key_features: str = "",
        uvp: str = "",
    ) -> dict:
        if formats is None:
            formats = ["blog", "instagram", "linkedin"]

        negative = (
            "blurry, low quality, distorted, ugly, cartoon, "
            "illustration, watermark, text, logo, people's faces, "
            "nsfw, violence, gore, noise, grainy"
        )

        if not self.bytez_client and not self.stability_api_key:
            print("[ImageGenerator] No Bytez or Stability API key - skipping")
            return {"images": {}, "error": "No image provider configured"}

        results = {}
        for fmt in formats:
            print(f"[ImageGenerator] Generating {fmt} image...")
            prompt = self._build_prompt(title, topic, mode, fmt, key_fact, key_features, uvp)
            img = self._call_provider(prompt, negative, fmt)
            if img:
                results[fmt] = img

        print(f"[ImageGenerator] Done - {len(results)}/{len(formats)} images generated")
        return {
            "images": results,
            "prompts_used": {
                fmt: self._build_prompt(title, topic, mode, fmt, key_fact, key_features, uvp)
                for fmt in formats
            },
        }

    def _build_prompt(
        self,
        title: str,
        topic: str,
        mode: str,
        fmt: str,
        key_fact: str = "",
        key_features: str = "",
        uvp: str = "",
    ) -> str:
        base = (
            f"Professional editorial visual for {fmt} content packaging. "
            f"Title context: '{title}'. Subject: {topic}. "
        )
        mode_style = self._mode_style(mode)
        message_style = self._message_guidance(mode, key_fact, key_features, uvp)
        format_style = self._format_style(fmt)
        composition = self._composition_guidance(fmt)
        return f"{base}{mode_style} {message_style} {format_style} {composition}"

    def _mode_style(self, mode: str) -> str:
        if mode == "product":
            return (
                "Premium commercial product scene, clean composition, modern brand aesthetic, "
                "studio lighting, sharp focus, realistic materials."
            )
        return (
            "Modern editorial business scene, strong composition, dramatic but professional lighting, "
            "realistic environment, technology or industry context."
        )

    def _format_style(self, fmt: str) -> str:
        if fmt == "instagram":
            return (
                "Instagram-first aesthetic, bold focal subject, cleaner background separation, "
                "slightly more cinematic lighting, visually striking, premium social-first look."
            )
        if fmt == "linkedin":
            return (
                "LinkedIn-first aesthetic, executive-friendly, polished corporate editorial style, "
                "credible business environment, restrained color palette, trustworthy and sharp."
            )
        return (
            "Blog-hero aesthetic, wide editorial framing, room for headline overlays, "
            "balanced composition, publication-ready."
        )

    def _message_guidance(self, mode: str, key_fact: str, key_features: str, uvp: str) -> str:
        if mode == "product":
            features = self._shorten(key_features, 160)
            benefit = self._shorten(uvp, 140)
            details = []
            if benefit:
                details.append(f"Primary value proposition: {benefit}.")
            if features:
                details.append(f"Important product cues: {features}.")
            if details:
                return " ".join(details)
            return "Show the product outcome clearly rather than abstract technology symbolism."

        fact = self._shorten(key_fact, 180)
        if fact:
            return (
                f"Visualize the news angle suggested by this fact: {fact}. "
                "Use symbolic but realistic business or industry cues that reinforce the claim."
            )
        return "Focus on the most concrete real-world implication of the news topic."

    def _composition_guidance(self, fmt: str) -> str:
        spec = self.FORMATS.get(fmt, self.FORMATS["blog"])
        if fmt == "instagram":
            framing = "Center-weighted composition with one clear hero subject and minimal clutter."
        elif fmt == "linkedin":
            framing = "Off-center composition with generous negative space for title overlays."
        else:
            framing = "Wide composition with clear visual hierarchy and room for article masthead text."
        return (
            f"{framing} Output size target {spec['width']}x{spec['height']}. "
            "No people, no text, no watermark."
        )

    def _call_provider(self, prompt: str, negative: str, fmt: str) -> dict | None:
        if self.bytez_client:
            image = self._call_bytez(prompt, negative, fmt)
            if image:
                return image
            print("[ImageGenerator] Bytez generation failed, trying Stability fallback")

        if self.stability_api_key:
            return self._call_stability(prompt, negative, fmt)

        return None

    def _call_bytez(self, prompt: str, negative: str, fmt: str) -> dict | None:
        spec = self.FORMATS.get(fmt, self.FORMATS["blog"])
        full_prompt = (
            f"{prompt} Output size target {spec['width']}x{spec['height']}. "
            f"Avoid: {negative}"
        )

        try:
            model = self.bytez_client.model(self.bytez_model_name)
            results = model.run(full_prompt)
        except Exception as exc:
            print(f"[ImageGenerator] Bytez request failed on {fmt}: {exc}")
            return None

        error = getattr(results, "error", None)
        if error:
            print(f"[ImageGenerator] Bytez error on {fmt}: {error}")
            return None

        output = getattr(results, "output", None)
        image_b64 = self._extract_image_b64(output)
        if not image_b64:
            print(f"[ImageGenerator] Bytez returned no usable image for {fmt}")
            return None

        filename = self._save_image(image_b64, fmt)
        print(f"[ImageGenerator] Saved Bytez image: {filename}")
        return {
            "path": filename,
            "base64": image_b64,
            "format": fmt,
            "label": spec["label"],
            "width": spec["width"],
            "height": spec["height"],
            "provider": "bytez",
            "model": self.bytez_model_name,
        }

    def _call_stability(self, prompt: str, negative: str, fmt: str) -> dict | None:
        spec = self.FORMATS.get(fmt, self.FORMATS["blog"])

        headers = {
            "Authorization": f"Bearer {self.stability_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0},
                {"text": negative, "weight": -1.0},
            ],
            "cfg_scale": 7,
            "steps": 30,
            "samples": 1,
            "width": spec["width"],
            "height": spec["height"],
        }

        try:
            resp = requests.post(self.API_URL, headers=headers, json=body, timeout=90)

            if resp.status_code == 401:
                print("[ImageGenerator] Invalid Stability API key")
                return None
            if resp.status_code == 402:
                print("[ImageGenerator] Stability credits exhausted")
                return None
            if resp.status_code != 200:
                print(f"[ImageGenerator] Stability API error {resp.status_code}: {resp.text[:300]}")
                return None

            data = resp.json()
            image_b64 = data["artifacts"][0]["base64"]
            filename = self._save_image(image_b64, fmt)

            print(f"[ImageGenerator] Saved Stability image: {filename}")
            return {
                "path": filename,
                "base64": image_b64,
                "format": fmt,
                "label": spec["label"],
                "width": spec["width"],
                "height": spec["height"],
                "provider": "stability",
                "model": "stable-diffusion-xl-1024-v1-0",
            }

        except requests.Timeout:
            print(f"[ImageGenerator] Timeout on {fmt} - Stability AI took too long")
            return None
        except Exception as exc:
            print(f"[ImageGenerator] Unexpected Stability error on {fmt}: {exc}")
            return None

    def _extract_image_b64(self, output) -> str | None:
        if not output:
            return None

        if isinstance(output, str):
            return self._extract_image_b64_from_string(output)

        if isinstance(output, list):
            for item in output:
                image_b64 = self._extract_image_b64(item)
                if image_b64:
                    return image_b64
            return None

        if isinstance(output, dict):
            for key in ("base64", "b64_json", "image_base64"):
                if output.get(key):
                    return self._normalize_b64(output[key])
            for key in ("output", "image", "images", "data", "artifacts", "result", "results"):
                if key in output:
                    image_b64 = self._extract_image_b64(output[key])
                    if image_b64:
                        return image_b64
            return None

        for attr in ("base64", "b64_json", "image_base64", "output", "image", "images", "data", "result", "results"):
            if hasattr(output, attr):
                image_b64 = self._extract_image_b64(getattr(output, attr))
                if image_b64:
                    return image_b64

        return None

    def _extract_image_b64_from_string(self, value: str) -> str | None:
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return self._download_image_as_b64(value)
        return self._normalize_b64(value)

    def _normalize_b64(self, value: str) -> str | None:
        if not value or not isinstance(value, str):
            return None
        if value.startswith("data:image"):
            _, _, tail = value.partition(",")
            return tail or None
        return value

    def _download_image_as_b64(self, url: str) -> str | None:
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code != 200:
                print(f"[ImageGenerator] Failed to download Bytez image {resp.status_code}: {url}")
                return None
            return base64.b64encode(resp.content).decode()
        except Exception as exc:
            print(f"[ImageGenerator] Failed to download Bytez image: {exc}")
            return None

    def _shorten(self, value: str, limit: int) -> str:
        if not value:
            return ""
        clean = " ".join(value.replace("\n", " ").replace("\r", " ").split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 3].rstrip() + "..."

    def _save_image(self, image_b64: str, fmt: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.img_dir}/{timestamp}_{fmt}.png"
        with open(filename, "wb") as file_obj:
            file_obj.write(base64.b64decode(image_b64))
        return filename
