import os
import unittest

# Set mock api keys before importing modules that instantiate API clients
os.environ["GROQ_API_KEY"] = "mock_groq_api_key"

from graph.blog_graph import _parse_blog

class TestBlogParser(unittest.TestCase):
    def test_parse_blog_with_markers(self):
        raw_content = """TITLE: Test Article Title
META_DESCRIPTION: This is a test meta description.
READING_TIME: 5 mins
WORD_COUNT: 1000
SEO_KEYWORDS: keyword1, keyword2, keyword3
TARGET_CTA: Click here to learn more
SOURCES_USED: source1.com, source2.org
---
Some metadata here
---
This is the actual blog content.
Line 2 of the content.
"""
        result = _parse_blog(raw_content)
        
        self.assertEqual(result.get("title"), "Test Article Title")
        self.assertEqual(result.get("meta_description"), "This is a test meta description.")
        self.assertEqual(result.get("reading_time"), "5 mins")
        self.assertEqual(result.get("word_count"), "1000")
        self.assertEqual(result.get("seo_keywords"), ["keyword1", "keyword2", "keyword3"])
        self.assertEqual(result.get("target_cta"), "Click here to learn more")
        self.assertEqual(result.get("sources_used"), ["source1.com", "source2.org"])
        self.assertEqual(result.get("content"), "This is the actual blog content.\nLine 2 of the content.")

    def test_parse_blog_without_markers(self):
        raw_content = "Just some plain text without any formatting markers."
        result = _parse_blog(raw_content)
        
        self.assertNotIn("title", result)
        self.assertEqual(result.get("content"), raw_content)

if __name__ == "__main__":
    unittest.main()
