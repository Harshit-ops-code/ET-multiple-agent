import requests
import base64
import os
from datetime import datetime
from config import STABILITY_API_KEY, OUTPUT_DIR


class ImageGenerator:
    """
    Generates images using Stability AI REST API directly.
    No grpcio or stability-sdk required — just requests.
    """

    # Stable Diffusion XL endpoint (no C++ compiler needed)
    API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    FORMATS = {
        "blog":      {"width": 1024, "height": 576,  "label": "Blog Hero (16:9)"},
        "instagram": {"width": 1024, "height": 1024, "label": "Instagram (1:1)"},
        "linkedin":  {"width": 1024, "height": 536,  "label": "LinkedIn (1.91:1)"},
    }

    def __init__(self):
        self.api_key = STABILITY_API_KEY
        self.img_dir = os.path.join(OUTPUT_DIR, "images")
        os.makedirs(self.img_dir, exist_ok=True)

    def generate(self, title: str, topic: str, mode: str,
                 formats: list = None) -> dict:
        if not self.api_key:
            print("[ImageGenerator] No Stability API key — skipping")
            return {"images": {}, "error": "No API key configured"}

        if formats is None:
            formats = ["blog", "instagram", "linkedin"]

        prompt   = self._build_prompt(title, topic, mode)
        negative = (
            "blurry, low quality, distorted, ugly, cartoon, "
            "illustration, watermark, text, logo, people's faces, "
            "nsfw, violence, gore, noise, grainy"
        )

        results = {}
        for fmt in formats:
            print(f"[ImageGenerator] Generating {fmt} image...")
            img = self._call_api(prompt, negative, fmt)
            if img:
                results[fmt] = img

        print(f"[ImageGenerator] Done — {len(results)}/{len(formats)} images generated")
        return {"images": results, "prompt_used": prompt}

    def _build_prompt(self, title: str, topic: str, mode: str) -> str:
        base = (
            f"Professional editorial photograph for article: '{title}'. "
            f"Subject: {topic}. "
        )
        if mode == "product":
            style = (
                "Clean product photography, minimalist white background, "
                "studio lighting, sharp focus, commercial quality, "
                "no people, no text, no watermarks"
            )
        else:
            style = (
                "Modern corporate photography, dramatic lighting, "
                "blue and white tones, high contrast, editorial style, "
                "technology or business environment, "
                "no people, no text, no watermarks, 4K quality"
            )
        return f"{base}{style}"

    def _call_api(self, prompt: str, negative: str, fmt: str) -> dict | None:
        spec = self.FORMATS.get(fmt, self.FORMATS["blog"])

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

        body = {
            "text_prompts": [
                {"text": prompt,   "weight": 1.0},
                {"text": negative, "weight": -1.0},
            ],
            "cfg_scale": 7,
            "steps":     30,
            "samples":   1,
            "width":     spec["width"],
            "height":    spec["height"],
        }

        try:
            resp = requests.post(
                self.API_URL,
                headers=headers,
                json=body,
                timeout=90,
            )

            if resp.status_code == 401:
                print("[ImageGenerator] Invalid API key")
                return None
            if resp.status_code == 402:
                print("[ImageGenerator] Insufficient credits")
                return None
            if resp.status_code != 200:
                print(f"[ImageGenerator] API error {resp.status_code}: {resp.text[:300]}")
                return None

            data      = resp.json()
            image_b64 = data["artifacts"][0]["base64"]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"{self.img_dir}/{timestamp}_{fmt}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(image_b64))

            print(f"[ImageGenerator] Saved: {filename}")
            return {
                "path":   filename,
                "base64": image_b64,
                "format": fmt,
                "label":  spec["label"],
                "width":  spec["width"],
                "height": spec["height"],
            }

        except requests.Timeout:
            print(f"[ImageGenerator] Timeout on {fmt} — Stability AI took too long")
            return None
        except Exception as e:
            print(f"[ImageGenerator] Unexpected error on {fmt}: {e}")
            return None