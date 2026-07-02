"""
Seed keyword list. Expand this freely — main.py iterates over all of these.
Organized by category purely for your own readability; scoring doesn't care.
"""

SEED_KEYWORDS = {
    "Core AI/ML": [
        "artificial intelligence developer",
        "machine learning engineer",
        "deep learning model",
        "AI model training",
        "AI algorithm development",
    ],
    "Computer Vision": [
        "computer vision developer",
        "object detection model",
        "image recognition AI",
        "OCR text extraction",
        "video analysis AI",
        "surveillance AI system",
    ],
    "NLP / LLM": [
        "NLP developer",
        "LLM application development",
        "AI chatbot development",
        "GPT integration",
        "RAG pipeline developer",
        "text classification AI",
        "sentiment analysis tool",
    ],
    "Generative AI": [
        "generative AI developer",
        "AI image generator setup",
        "AI content generation tool",
        "stable diffusion developer",
        "AI avatar generator",
    ],
    "Automation / Agents": [
        "AI automation expert",
        "AI agent developer",
        "n8n automation expert",
        "zapier automation expert",
        "workflow automation AI",
        "AI voice agent",
    ],
    "Data Science / Analytics": [
        "data science consultant",
        "predictive analytics model",
        "recommendation system developer",
        "AI dashboard developer",
        "data analysis AI",
    ],
    "Niche Verticals": [
        "healthcare AI developer",
        "AI fitness app",
        "AI SaaS MVP developer",
        "AI consulting services",
        "AI chatbot for ecommerce",
        "AI customer support bot",
    ],
}


def flatten_keywords():
    """Returns a flat list of all keywords across categories."""
    all_kw = []
    for category, kws in SEED_KEYWORDS.items():
        all_kw.extend(kws)
    return all_kw