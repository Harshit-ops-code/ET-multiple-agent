from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.blog_writer import BlogWriterAgent

app = Flask(__name__)
CORS(app)

writer = BlogWriterAgent()

@app.route('/generate', methods=['POST'])
def generate_blog():
    data = request.get_json()

    topic    = data.get('topic', '')
    audience = data.get('audience', 'general professional audience')
    length   = int(data.get('length', 1000))
    context  = data.get('context', '')

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    try:
        result = writer.generate(
            topic=topic,
            audience=audience,
            length=length,
            context=context,
        )
        return jsonify({
            'success': True,
            'title':            result.get('title', 'Untitled'),
            'meta_description': result.get('meta_description', ''),
            'reading_time':     result.get('reading_time', ''),
            'seo_keywords':     result.get('seo_keywords', []),
            'content':          result.get('content', result.get('raw', '')),
            'sources':          result.get('sources', []),        # ← new
            'tavily_answer':    result.get('tavily_answer', ''),  # ← new
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)