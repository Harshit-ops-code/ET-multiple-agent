#!/usr/bin/env python
"""
Quick test script to verify the app works with mock LLM fallback.
Tests without network access or API keys.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("[Test] Starting blog generation test...")
print("[Test] Python version:", sys.version)
print()

try:
    from agents.blog_writer import BlogWriterAgent
    
    print("[Test] BlogWriterAgent imported successfully")
    print("[Test] Initializing agent...")
    
    writer = BlogWriterAgent()
    
    print("[Test] Agent initialized. Starting generation...")
    print()
    
    result = writer.generate(
        topic="Why most startups fail at content marketing",
        audience="startup founders and early-stage marketers",
        length=1000,
        use_web_search=False,
    )
    
    print("\n" + "="*60)
    print("✅ GENERATION SUCCESSFUL!")
    print("="*60)
    print(f"Title:        {result.get('title', 'N/A')}")
    print(f"Reading time: {result.get('reading_time', 'N/A')}")
    print(f"Keywords:     {result.get('seo_keywords', [])}")
    print("\nContent preview (first 300 chars):")
    print(result.get("content", "")[:300])
    print("\n" + "="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"Details: {str(e)[:200]}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
