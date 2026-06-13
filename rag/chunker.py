# rag/chunker.py

def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    """
    Split text into chunks of chunk_size with chunk_overlap.
    Attempts to break on paragraph or sentence boundaries.
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        # If we have reached the end, grab everything remaining
        if start + chunk_size >= text_len:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break
            
        end = start + chunk_size
        
        # Look back up to 25% of chunk_size to find a nice boundary
        lookback = int(chunk_size * 0.25)
        boundary = -1
        
        # Priority boundaries: paragraphs, newlines, sentences
        for separator in ["\n\n", "\n", ". ", "? ", "! "]:
            pos = text.rfind(separator, end - lookback, end)
            if pos != -1:
                boundary = pos + len(separator)
                break
                
        if boundary != -1:
            end = boundary
            
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # Move start point back by overlap
        start = end - chunk_overlap
        
        # Avoid infinite loops if chunk_overlap >= chunk_size
        if start >= end:
            start = end - 1
            
    return chunks
