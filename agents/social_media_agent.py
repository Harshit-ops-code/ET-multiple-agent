from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.image_generator import ImageGenerator
from prompts.social_media_prompt import (
    INSTAGRAM_NEWS_CAPTION,
    INSTAGRAM_PRODUCT_CAPTION,
    LINKEDIN_NEWS_CAPTION,
    LINKEDIN_PRODUCT_CAPTION,
    KEY_FACT_EXTRACTOR,
)
from config import GROQ_API_KEY, GROQ_MODEL, BRAND_NAME, OUTPUT_DIR
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, io, base64, textwrap, re
from datetime import datetime


# Standard sizes — same 4:5 ratio for both platforms (works on both)
INSTAGRAM_SIZE = (1080, 1080)   # 1:1 square
LINKEDIN_SIZE  = (1200, 628)    # 1.91:1 landscape


class SocialMediaAgent:

    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.75,
            max_tokens=800,
        )
        self.img_gen  = ImageGenerator()
        self.post_dir = os.path.join(OUTPUT_DIR, "social_posts")
        os.makedirs(self.post_dir, exist_ok=True)

    def generate(self, blog_data: dict, mode: str,
                 platforms: list = None,
                 user_image_b64: str = None) -> dict:
        """
        Generate social media posts.
        user_image_b64: optional base64 image uploaded by user
        """
        if platforms is None:
            platforms = ["instagram", "linkedin"]

        topic        = blog_data.get("topic", "")
        title        = blog_data.get("title", topic)
        content      = blog_data.get("content", "")
        key_features = blog_data.get("key_features", "")
        uvp          = blog_data.get("uvp", "")
        audience     = blog_data.get("audience", "professionals")

        # Extract key fact for news mode
        key_fact = self._extract_key_fact(content) if mode == "news" else ""

        results = {}
        for platform in platforms:
            print(f"\n[SocialMediaAgent] {platform} {mode} post...")
            try:
                if platform == "instagram":
                    results["instagram"] = self._make_instagram(
                        topic, title, mode, content, key_fact,
                        key_features, uvp, user_image_b64
                    )
                elif platform == "linkedin":
                    results["linkedin"] = self._make_linkedin(
                        topic, title, mode, content, key_fact,
                        key_features, uvp, audience, user_image_b64
                    )
            except Exception as e:
                print(f"[SocialMediaAgent] {platform} error: {e}")
                import traceback; traceback.print_exc()
                results[platform] = {"error": str(e)}

        return results

    # ── INSTAGRAM ─────────────────────────────────────────────────

    def _make_instagram(self, topic, title, mode, content, key_fact,
                         key_features, uvp, user_image_b64) -> dict:
        # 1. Caption
        caption = self._caption(
            INSTAGRAM_NEWS_CAPTION if mode == "news" else INSTAGRAM_PRODUCT_CAPTION,
            topic=topic, key_fact=key_fact, brand=BRAND_NAME,
            key_features=key_features, uvp=uvp,
        )

        # 2. Background image
        bg_b64 = user_image_b64 or self._gen_background(
            topic, title, mode, "instagram", key_fact, key_features, uvp
        )

        # 3. Render overlay
        image_b64 = self._render_instagram(bg_b64, title, mode, key_fact, key_features)
        path      = self._save(image_b64, "instagram")

        return {
            "caption":    caption,
            "image_b64":  image_b64,
            "image_path": path,
            "size":       "1080x1080 (Instagram square)",
            "platform":   "instagram",
        }

    # ── LINKEDIN ──────────────────────────────────────────────────

    def _make_linkedin(self, topic, title, mode, content, key_fact,
                        key_features, uvp, audience, user_image_b64) -> dict:
        # 1. Post text
        post_text = self._caption(
            LINKEDIN_NEWS_CAPTION if mode == "news" else LINKEDIN_PRODUCT_CAPTION,
            topic=topic, key_fact=key_fact, brand=BRAND_NAME,
            key_features=key_features, uvp=uvp, audience=audience,
        )

        # 2. Background
        bg_b64 = user_image_b64 or self._gen_background(
            topic, title, mode, "linkedin", key_fact, key_features, uvp
        )

        # 3. Render
        image_b64 = self._render_linkedin(bg_b64, title, mode, key_fact, key_features)
        path      = self._save(image_b64, "linkedin")

        return {
            "post_text":  post_text,
            "image_b64":  image_b64,
            "image_path": path,
            "size":       "1200x628 (LinkedIn landscape)",
            "platform":   "linkedin",
        }

    # ── CAPTION GENERATION ────────────────────────────────────────

    def _caption(self, template: str, **kwargs) -> str:
        needed   = set(re.findall(r'\{(\w+)\}', template))
        filtered = {k: v for k, v in kwargs.items() if k in needed}
        # Fill missing keys with empty string
        for k in needed:
            if k not in filtered:
                filtered[k] = ""
        prompt = ChatPromptTemplate.from_messages([("human", template)])
        chain  = prompt | self.llm | StrOutputParser()
        return chain.invoke(filtered).strip()

    def _extract_key_fact(self, content: str) -> str:
        if not content:
            return ""
        prompt = ChatPromptTemplate.from_messages([("human", KEY_FACT_EXTRACTOR)])
        chain  = prompt | self.llm | StrOutputParser()
        return chain.invoke({"content": content[:1500]}).strip()

    # ── BACKGROUND GENERATION ─────────────────────────────────────

    def _gen_background(self, topic, title, mode, platform, key_fact="", key_features="", uvp="") -> str | None:
        result  = self.img_gen.generate(
            title=title,
            topic=topic,
            mode=mode,
            formats=[platform],
            key_fact=key_fact,
            key_features=key_features,
            uvp=uvp,
        )
        img = result.get("images", {}).get(platform)
        return img.get("base64") if img else None

    # ── INSTAGRAM RENDERER (1080x1080) ────────────────────────────

    def _render_instagram(self, bg_b64, title, mode, key_fact, key_features) -> str:
        W, H = INSTAGRAM_SIZE

        # Base canvas
        if bg_b64:
            raw = base64.b64decode(bg_b64)
            bg  = Image.open(io.BytesIO(raw)).convert("RGB")
            bg  = bg.resize((W, H), Image.LANCZOS)
            # Slightly blur background for text readability
            bg  = bg.filter(ImageFilter.GaussianBlur(radius=2))
        else:
            bg = Image.new("RGB", (W, H), (15, 15, 30))

        canvas = bg.convert("RGBA")

        # Full dark overlay (stronger at bottom)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        # Top bar
        od.rectangle([(0, 0), (W, 90)], fill=(0, 0, 0, 180))
        # Bottom gradient (manual bands)
        for i in range(H // 2):
            alpha = int(210 * (i / (H // 2)))
            od.rectangle([(0, H // 2 + i), (W, H // 2 + i + 1)],
                         fill=(0, 0, 0, alpha))
        canvas = Image.alpha_composite(canvas, overlay)
        draw   = ImageDraw.Draw(canvas)

        # Colors
        WHITE  = (255, 255, 255)
        GOLD   = (255, 200, 50)
        ACCENT = (124, 109, 250) if mode == "news" else (45, 212, 191)
        MUTED  = (200, 200, 220)

        # Top accent bar (6px)
        draw.rectangle([(0, 0), (W, 7)], fill=ACCENT)

        # Brand name — top left
        font_brand = self._font(26, bold=True)
        draw.text((32, 22), BRAND_NAME.upper(), font=font_brand, fill=ACCENT)

        # Mode tag — top right
        tag = "BREAKING NEWS" if mode == "news" else "PRODUCT LAUNCH"
        font_tag = self._font(20, bold=True)
        bbox = draw.textbbox((0, 0), tag, font=font_tag)
        tw   = bbox[2] - bbox[0]
        # Pill background
        pad  = 10
        draw.rounded_rectangle(
            [(W - tw - pad*2 - 32, 18), (W - 32, 62)],
            radius=20, fill=(*ACCENT, 220)
        )
        draw.text((W - tw - pad - 32, 30), tag, font=font_tag, fill=WHITE)

        # Main headline — center, large
        clean_title = title.replace("#", "").strip()
        words       = clean_title.split()
        headline    = " ".join(words[:7])
        if len(words) > 7:
            headline += "..."

        font_h  = self._font(72, bold=True)
        wrapped = textwrap.wrap(headline.upper(), width=16)
        y       = H - 460
        for line in wrapped[:3]:
            bbox = draw.textbbox((0, 0), line, font=font_h)
            lw   = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, y), line, font=font_h, fill=WHITE)
            y += 84

        # Key fact / stat highlight pill
        if key_fact:
            kf_clean = key_fact.replace("\\n", " ").replace("\\r", " ").strip()
            fact_short = kf_clean[:60] + "…" if len(kf_clean) > 60 else kf_clean
            font_fact  = self._font(28, bold=True)
            bbox       = draw.textbbox((0, 0), fact_short, font=font_fact)
            fw         = bbox[2] - bbox[0]
            pill_w     = min(fw + 60, W - 80)
            pill_x     = (W - pill_w) // 2
            y += 10
            draw.rounded_rectangle(
                [(pill_x, y), (pill_x + pill_w, y + 56)],
                radius=28, fill=(*GOLD[:3], 220)
            )
            draw.text((W // 2 - fw // 2, y + 14),
                      fact_short, font=font_fact, fill=(20, 20, 20))
            y += 76

        # Feature bullets (product) or short points (news)
        font_b = self._font(28)
        bullets = []
        if mode == "product" and key_features:
            bullets = [f.strip().replace("\\n", " ") for f in re.split(r'[,\\n\\r]+', key_features) if f.strip()][:3]
            icons   = ["🚀", "💡", "🔒"]
        else:
            # Extract 2 short sentences from key_fact
            kf_clean = key_fact.replace("\\n", " ").replace("\\r", " ").strip() if key_fact else ""
            bullets = [kf_clean[:55]] if kf_clean else []
            icons   = ["📌"]

        y += 10
        for icon, bullet in zip(icons, bullets):
            short = bullet[:50] + "…" if len(bullet) > 50 else bullet
            text  = f"{icon}  {short}"
            draw.text((60, y), text, font=font_b, fill=MUTED)
            y += 44

        # Bottom bar
        draw.rectangle([(0, H - 70), (W, H)], fill=(*ACCENT[:3], 200))
        font_cta = self._font(26, bold=True)
        cta_text = f"Follow @{BRAND_NAME.lower()} for more  🔗"
        bbox     = draw.textbbox((0, 0), cta_text, font=font_cta)
        cw       = bbox[2] - bbox[0]
        draw.text(((W - cw) // 2, H - 48), cta_text, font=font_cta, fill=WHITE)

        return self._to_b64(canvas)

    # ── LINKEDIN RENDERER (1200x628) ──────────────────────────────

    def _render_linkedin(self, bg_b64, title, mode, key_fact, key_features) -> str:
        W, H = LINKEDIN_SIZE

        # Background
        if bg_b64:
            raw = base64.b64decode(bg_b64)
            bg  = Image.open(io.BytesIO(raw)).convert("RGB")
            bg  = bg.resize((W, H), Image.LANCZOS)
            bg  = bg.filter(ImageFilter.GaussianBlur(radius=3))
        else:
            bg = Image.new("RGB", (W, H), (8, 20, 45))

        canvas = bg.convert("RGBA")

        # Left dark panel (55% width)
        panel_w = int(W * 0.56)
        panel   = Image.new("RGBA", (panel_w, H), (8, 14, 36, 242))
        canvas.alpha_composite(panel, dest=(0, 0))

        # Right: vignette
        ov = Image.new("RGBA", (W - panel_w, H), (0, 0, 0, 100))
        canvas.alpha_composite(ov, dest=(panel_w, 0))

        draw = ImageDraw.Draw(canvas)

        # Colors — corporate LinkedIn palette
        BLUE   = (24, 95, 165)
        WHITE  = (255, 255, 255)
        SILVER = (170, 185, 210)
        GOLD   = (240, 192, 80)
        ACCENT = (45, 212, 191) if mode == "product" else (56, 138, 221)

        # Left accent bar (5px vertical)
        draw.rectangle([(0, 0), (5, H)], fill=ACCENT)

        # Brand name
        font_brand = self._font(22, bold=True)
        draw.text((28, 28), BRAND_NAME.upper(), font=font_brand, fill=ACCENT)

        # Mode label
        font_label = self._font(14)
        label = "PRODUCT LAUNCH" if mode == "product" else "NEWS & ANALYSIS"
        draw.text((28, 56), label, font=font_label, fill=SILVER)

        # Thin divider
        draw.rectangle([(28, 78), (panel_w - 30, 80)],
                       fill=(*BLUE[:3], 100))

        # Headline
        clean  = title.replace("#", "").strip()
        font_h = self._font(48, bold=True)
        wrapped = textwrap.wrap(clean, width=24)
        y = 96
        for line in wrapped[:3]:
            draw.text((28, y), line, font=font_h, fill=WHITE)
            y += 56

        # Stat / key fact box
        if key_fact:
            kf_clean = key_fact.replace("\\n", " ").replace("\\r", " ").strip()
            fact_s = kf_clean[:75] + "…" if len(kf_clean) > 75 else kf_clean
            font_f = self._font(20, bold=True)
            y += 8
            draw.rounded_rectangle(
                [(28, y), (panel_w - 30, y + 44)],
                radius=6,
                fill=(*ACCENT[:3], 35),
                outline=(*ACCENT[:3], 150),
                width=1,
            )
            draw.text((44, y + 10), fact_s, font=font_f, fill=GOLD)
            y += 58

        # Feature points
        font_b = self._font(20)
        bullets = []
        if mode == "product" and key_features:
            bullets = [f.strip().replace("\\n", " ") for f in re.split(r'[,\\n\\r]+', key_features) if f.strip()][:3]
        elif key_fact:
            kf_clean = key_fact.replace("\\n", " ").replace("\\r", " ").strip()
            bullets = [kf_clean[:65]]

        y += 4
        for b in bullets:
            short = b[:65] + "…" if len(b) > 65 else b
            # Dot
            draw.ellipse([(28, y + 9), (38, y + 19)], fill=ACCENT)
            draw.text((50, y + 2), short, font=font_b, fill=SILVER)
            y += 36

        # Bottom bar
        draw.rectangle([(0, H - 52), (panel_w, H)],
                       fill=(*BLUE[:3], 210))
        font_cta = self._font(18, bold=True)
        draw.text((28, H - 36),
                  f"{BRAND_NAME} | Professional Insights",
                  font=font_cta, fill=WHITE)

        # Right side large brand initial (watermark style)
        font_wm = self._font(160, bold=True)
        initial = BRAND_NAME[0].upper()
        bbox    = draw.textbbox((0, 0), initial, font=font_wm)
        iw, ih  = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (panel_w + (W - panel_w - iw) // 2, (H - ih) // 2),
            initial, font=font_wm, fill=(*WHITE, 18)
        )

        return self._to_b64(canvas)

    # ── HELPERS ───────────────────────────────────────────────────

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        paths = []
        if bold:
            paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        else:
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

    def _to_b64(self, img: Image.Image) -> str:
        rgb    = img.convert("RGB")
        buf    = io.BytesIO()
        rgb.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()

    def _save(self, b64: str, platform: str) -> str:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.post_dir}/{ts}_{platform}.png"
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path
