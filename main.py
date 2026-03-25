from agents.blog_writer import BlogWriterAgent

def main():
    writer = BlogWriterAgent()

    result = writer.generate(
        topic="Why most startups fail at content marketing",
        audience="startup founders and early-stage marketers",
        length=1000,
    )

    print("\n" + "="*60)
    print("GENERATED BLOG")
    print("="*60)
    print(f"Title:        {result.get('title', 'N/A')}")
    print(f"Reading time: {result.get('reading_time', 'N/A')}")
    print(f"Keywords:     {result.get('seo_keywords', [])}")
    print("\n--- CONTENT PREVIEW (first 500 chars) ---")
    print(result.get("content", "")[:500])

if __name__ == "__main__":
    main()