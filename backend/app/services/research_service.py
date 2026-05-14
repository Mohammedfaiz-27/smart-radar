"""
AI-powered research service using Gemini (primary) and OpenAI (fallback)
"""
import os
import logging
from typing import Optional

import google.generativeai as genai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_openai_client: Optional[AsyncOpenAI] = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def _call_gemini(system: str, user: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system,
    )
    response = model.generate_content(user)
    return response.text


async def _call_openai(system: str, user: str) -> str:
    resp = await _openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content


async def _call_ai(system: str, user: str) -> str:
    """Call Gemini first; fall back to OpenAI on failure."""
    if GEMINI_API_KEY:
        try:
            return await _call_gemini(system, user)
        except Exception as e:
            logger.warning(f"Gemini failed, falling back to OpenAI: {e}")
    if _openai_client:
        return await _call_openai(system, user)
    raise RuntimeError("No AI API key configured (GEMINI_API_KEY or OPENAI_API_KEY required)")


async def get_understanding(query: str) -> str:
    return await _call_ai(
        "You are a knowledgeable assistant. Provide a brief, clear understanding of any topic in 2-3 sentences. Be concise and informative.",
        f"Explain what '{query}' is in 2-3 sentences. Be clear and concise.",
    )


async def get_history(query: str, understanding: Optional[str] = None) -> str:
    context = f"Context: {understanding}\n\n" if understanding else ""
    return await _call_ai(
        "You are a historical research expert. Provide detailed historical information about topics, including key events, developments, and evolution over time.",
        f"{context}Provide detailed historical information about '{query}'. Include key events, developments, milestones, and how it has evolved over time.",
    )


async def get_current_affairs(query: str, understanding: Optional[str] = None) -> str:
    context = f"Context: {understanding}\n\n" if understanding else ""
    return await _call_ai(
        "You are a current affairs expert. Provide up-to-date information about recent developments, news, and current issues related to any topic.",
        f"{context}Provide detailed current affairs and recent developments about '{query}'. Include recent news, current issues, latest developments, and ongoing trends.",
    )


async def get_competitors(query: str, understanding: Optional[str] = None) -> str:
    context = f"Context: {understanding}\n\n" if understanding else ""
    return await _call_ai(
        "You are a competitive analysis expert. Identify and analyze competitors, alternatives, or similar entities in any domain.",
        f"{context}Identify and analyze competitors, alternatives, or similar entities related to '{query}'. Include key players, their strengths, market position, and competitive dynamics.",
    )


async def get_challenges(query: str, understanding: Optional[str] = None) -> str:
    context = f"Context: {understanding}\n\n" if understanding else ""
    return await _call_ai(
        "You are an expert at identifying challenges and problems. Analyze any topic to identify key challenges, obstacles, and difficulties.",
        f"{context}Identify and analyze the key challenges, problems, obstacles, and difficulties related to '{query}'. Include current issues, potential problems, and systemic challenges.",
    )


async def get_plus_points(query: str, understanding: Optional[str] = None) -> str:
    context = f"Context: {understanding}\n\n" if understanding else ""
    return await _call_ai(
        "You are an expert at identifying positive aspects and advantages. Analyze any topic to highlight strengths, benefits, and positive qualities.",
        f"{context}Identify and analyze the positive aspects, advantages, strengths, and benefits related to '{query}'. Include key strengths, unique advantages, and positive qualities.",
    )


async def get_negative_points(query: str, understanding: Optional[str] = None) -> str:
    context = f"Context: {understanding}\n\n" if understanding else ""
    return await _call_ai(
        "You are an expert at identifying negative aspects and disadvantages. Analyze any topic to highlight weaknesses, drawbacks, and negative qualities.",
        f"{context}Identify and analyze the negative aspects, disadvantages, weaknesses, and drawbacks related to '{query}'. Include key weaknesses, potential issues, and negative qualities.",
    )


async def generate_social_posts(query: str, about: Optional[str] = None, current_affairs: Optional[str] = None) -> dict:
    import json, re
    context = ""
    if about:
        context += f"About: {about}\n\n"
    if current_affairs:
        context += f"Current Affairs: {current_affairs}\n\n"

    result = await _call_ai(
        (
            "You are a social media content creator. Generate engaging social media posts based on the topic and research provided. "
            "Return ONLY valid JSON with keys 'facebook_posts' and 'twitter_posts'. "
            "Each key maps to an array of objects with 'content' (string) and 'call_to_action' (string) fields."
        ),
        f"{context}Generate 3 Facebook posts and 3 Twitter/X posts about '{query}'. Return valid JSON only.",
    )
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"facebook_posts": [], "twitter_posts": []}
