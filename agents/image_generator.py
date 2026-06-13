import base64
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont

from config import BYTEZ_API_KEY, BYTEZ_IMAGE_MODEL, OUTPUT_DIR, STABILITY_API_KEY, GEMINI_API_KEY

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
        self.gemini_api_key = GEMINI_API_KEY
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

        if not self.gemini_api_key and not self.bytez_client and not self.stability_api_key:
            print("[ImageGenerator] No Gemini, Bytez or Stability API key - skipping")
            return {"images": {}, "error": "No image provider configured"}

        results = {}
        max_workers = min(len(formats), 3)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for fmt in formats:
                prompt = self._build_prompt(title, topic, mode, fmt, key_fact, key_features, uvp)
                print(f"[ImageGenerator] Queueing {fmt} image...")
                future = executor.submit(self._call_provider, prompt, negative, fmt)
                future_map[future] = fmt

            for future in as_completed(future_map):
                fmt = future_map[future]
                try:
                    img = future.result()
                except Exception as exc:
                    print(f"[ImageGenerator] Unexpected async error on {fmt}: {exc}")
                    img = None
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
        if self.gemini_api_key:
            image = self._call_gemini(prompt, fmt)
            if image:
                return image
            print("[ImageGenerator] Gemini generation failed, trying Bytez fallback")

        if self.bytez_client:
            image = self._call_bytez(prompt, negative, fmt)
            if image:
                return image
            print("[ImageGenerator] Bytez generation failed, trying Stability fallback")

        if self.stability_api_key:
            image = self._call_stability(prompt, negative, fmt)
            if image:
                return image

        print(f"[ImageGenerator] All API providers failed for {fmt} - generating beautiful offline fallback placeholder")
        return self._create_fallback_image(prompt, fmt)

    def _call_gemini(self, prompt: str, fmt: str) -> dict | None:
        spec = self.FORMATS.get(fmt, self.FORMATS["blog"])
        aspect_ratio = "1:1"
        if fmt == "blog":
            aspect_ratio = "16:9"
        elif fmt == "linkedin":
            aspect_ratio = "16:9"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={self.gemini_api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }

        body = {
            "instances": [
                {"prompt": prompt}
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": aspect_ratio,
                "outputMimeType": "image/jpeg"
            }
        }

        try:
            print(f"[ImageGenerator] Requesting Gemini Imagen image for {fmt} with aspect ratio {aspect_ratio}...")
            resp = requests.post(url, headers=headers, json=body, timeout=90)
            if resp.status_code != 200:
                print(f"[ImageGenerator] Gemini Imagen API error {resp.status_code}: {resp.text[:300]}")
                return None

            data = resp.json()
            predictions = data.get("predictions", [])
            if not predictions:
                print("[ImageGenerator] Gemini Imagen returned no predictions")
                return None

            prediction = predictions[0]
            image_b64 = prediction.get("bytesBase64Encoded")
            if not image_b64 and "image" in prediction:
                image_b64 = prediction["image"].get("imageBytes")

            if not image_b64:
                print("[ImageGenerator] Gemini Imagen prediction has no image bytes")
                return None

            filename = self._save_image(image_b64, fmt)
            print(f"[ImageGenerator] Saved Gemini image: {filename}")
            return {
                "path": filename,
                "base64": image_b64,
                "format": fmt,
                "label": spec["label"],
                "width": spec["width"],
                "height": spec["height"],
                "provider": "gemini",
                "model": "imagen-3.0-generate-002",
            }

        except Exception as exc:
            print(f"[ImageGenerator] Unexpected Gemini Imagen error on {fmt}: {exc}")
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
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.img_dir}/{timestamp}_{fmt}.png"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "wb") as file_obj:
                file_obj.write(base64.b64decode(image_b64))
            return filename
        except Exception as e:
            print(f"[ImageGenerator] Warning: Failed to save image to disk: {e}")
            return ""

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        from PIL import ImageFont
        paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _create_fallback_image(self, prompt: str, fmt: str) -> dict:
        from PIL import Image, ImageDraw, ImageFont
        spec = self.FORMATS.get(fmt, self.FORMATS["blog"])
        w, h = spec["width"], spec["height"]
        
        # Slate 800 background
        img = Image.new("RGB", (w, h), (15, 23, 42))
        draw = ImageDraw.Draw(img)
        
        # Draw elegant modern tech grid and glow
        grid_size = 40
        for x in range(0, w, grid_size):
            draw.line([(x, 0), (x, h)], fill=(30, 41, 59), width=1)
        for y in range(0, h, grid_size):
            draw.line([(0, y), (w, y)], fill=(30, 41, 59), width=1)
            
        # Draw double border with color accents matching premium design (Indigo to Teal gradient)
        border_col = (99, 102, 241) if fmt == "instagram" else (20, 184, 166) if fmt == "linkedin" else (168, 85, 247)
        draw.rectangle([(20, 20), (w - 20, h - 20)], outline=border_col, width=3)
        draw.rectangle([(25, 25), (w - 25, h - 25)], outline=(30, 41, 59), width=1)
        
        # Load a nice bold font for subtitle
        font = self._font(min(w, h) // 12)
        font_sm = self._font(min(w, h) // 20)
        
        title_text = "LE-XIS AI"
        subtitle_text = f"GENAI IMAGE: {fmt.upper()} ({w}x{h})"
        
        # Draw text centered
        bbox = draw.textbbox((0, 0), title_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        bbox_sm = draw.textbbox((0, 0), subtitle_text, font=font_sm)
        tw_sm = bbox_sm[2] - bbox_sm[0]
        th_sm = bbox_sm[3] - bbox_sm[1]
        
        # Center title
        draw.text(((w - tw) // 2, (h // 2) - th - 10), title_text, font=font, fill=(255, 255, 255))
        # Center subtitle
        draw.text(((w - tw_sm) // 2, (h // 2) + 10), subtitle_text, font=font_sm, fill=border_col)
        
        # Export base64
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_b64 = base64.b64encode(buf.getvalue()).decode()
        
        filename = self._save_image(image_b64, fmt)
        
        return {
            "path": filename,
            "base64": image_b64,
            "format": fmt,
            "label": spec["label"],
            "width": w,
            "height": h,
            "provider": "offline_fallback",
            "model": "pil_premium_generator",
        }
