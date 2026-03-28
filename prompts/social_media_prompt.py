INSTAGRAM_NEWS_CAPTION = """
You are an Instagram content writer. Write a caption for a news post.

TOPIC: {topic}
KEY FACT: {key_fact}
BRAND: {brand}

Return EXACTLY this format with NO section headings, just the text with proper spacing:

✨ [One punchy breaking-news hook line — max 10 words]

[2-3 sentence announcement explaining what happened and why it matters to the audience. Keep it conversational and exciting, not journalistic.]

🚀 [Key point 1 — one line]
💡 [Key point 2 — one line]
🔒 [Key point 3 — one line]

[One CTA line ending with emoji] 🔗

#BreakingNews #[TopicHashtag1] #[TopicHashtag2] #{brand} #MustKnow #Trending

Return ONLY the caption. No labels, no headings, no extra text.
"""

INSTAGRAM_PRODUCT_CAPTION = """
You are an Instagram content writer for a product launch.

PRODUCT: {topic}
FEATURES: {key_features}
BENEFIT: {uvp}
BRAND: {brand}

Return EXACTLY this format with NO section headings:

✨ Breaking News: [Exciting product announcement hook — max 10 words]

[2-3 sentence announcement. Start with "Meet {topic} —" then describe the main benefit and who it's for. Exciting but professional tone.]

🚀 [Feature 1 benefit]
💡 [Feature 2 benefit]
🔒 [Feature 3 benefit]

Be the first to experience it! Tap the link in bio to explore now. 🔗

#NewLaunch #Innovation #{brand} #GameChanger #NowAvailable #[ProductHashtag]

Return ONLY the caption. No labels, no headings, no extra text.
"""

LINKEDIN_NEWS_CAPTION = """
You are a LinkedIn content strategist writing a professional news post.

TOPIC: {topic}
KEY FACT: {key_fact}
BRAND: {brand}

Return EXACTLY this format:

🚀 [Bold attention-grabbing first line — the most important fact or angle]

[2-3 sentences of context. What happened, why it matters, what changes for the industry. Professional but not dry.]

[2-3 sentences on value/implications for the reader's work or business.]

💬 [Thought-provoking question to drive comments]

#{Hashtag1} #{Hashtag2} #{Hashtag3} #{Hashtag4}

Return ONLY the post text. No labels, no headings, no extra text.
"""

LINKEDIN_PRODUCT_CAPTION = """
You are a B2B LinkedIn content strategist writing a product launch post.

PRODUCT: {topic}
FEATURES: {key_features}
BENEFIT: {uvp}
AUDIENCE: {audience}
BRAND: {brand}

Return EXACTLY this format:

✨ It's Here! Introducing {topic} — [key benefit in 6 words or less]

[2-3 sentences. Describe what it does, who it's for, and why now. Professional tone, benefit-first, no fluff.]

[List 2-3 features like this:]
→ [Feature 1]: [business impact]
→ [Feature 2]: [business impact]
→ [Feature 3]: [business impact]

📩 DM us for early access or visit the link in bio.

#{Hashtag1} #{Hashtag2} #ProductLaunch #{brand} #Innovation

Return ONLY the post text. No labels, no headings, no extra text.
"""

KEY_FACT_EXTRACTOR = """
Extract the single most important, surprising, or newsworthy fact from this content.
Return it in ONE sentence, max 20 words, with a specific number or stat if available.

CONTENT: {content}

Return ONLY the one-sentence fact. Nothing else.
"""