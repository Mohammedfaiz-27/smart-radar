#!/usr/bin/env python3
"""
City Research App - Main runner script

Setup Instructions:
1. Copy .env.example to .env and fill in your API keys
2. Install dependencies: uv sync
3. Install Playwright browsers: playwright install chromium
4. Run the app: python run.py

Features:
- City research using OpenAI and Perplexity APIs
- Knowledge graph generation and visualization
- Social media handles generation
- HTML content generation with OpenAI
- Screenshot generation with Playwright
- Facebook posting capability
"""

import uvicorn
import os
from dotenv import load_dotenv


def main():
    load_dotenv()

    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY", "PERPLEXITY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and fill in your API keys")
        return

    print("🚀 Starting City Research App...")
    print("📍 Home page: http://localhost:8000")
    print("📄 Post page: http://localhost:8000/post")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[".", "services", "templates", "api"],
    )


if __name__ == "__main__":
    main()
