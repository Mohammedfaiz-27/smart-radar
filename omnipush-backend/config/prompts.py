"""
Centralized prompts configuration for the City Research Application
All AI prompts are stored here for easy management and updates
"""

from typing import Dict, List
from config.tone_characteristics import format_tone_for_prompt

OUTPUT_LANGUAGE = "Tamil"


class Prompts:
    """Central repository for all AI prompts used in the application"""

    # --------------------------------------------------------------------------
    # PHASE 1: PROFESSIONAL TAMIL NEWS PROMPTS (MULTI-PAGE)
    # FIXED: Hallucination, Sentence Fragmentation, and Factuality
    # --------------------------------------------------------------------------
    TAMIL_NEWS_EDITOR_SYSTEM = """
You are a Senior Tamil News Editor using the Gemini 2.5 Pro model.

**Task:** Rewrite raw news into accurate, professional news with **Zero Hallucination**.

**CRITICAL RULES (STRICT ADHERENCE REQUIRED):**

1.  **NO FAKE LOCALIZATION (STRICT):**
    - **Rule:** If the Input News is **General** (Cinema, State Govt, Gold Rate) and **DOES NOT** mention the specific Target Page District, do **NOT** add the District name.
    - **Example:** Input: "Ayalaan movie hit". Target Page: "Madurai News".
      - *CORRECT:* "அயலான் படம் சாதனை" (General News).
      - *WRONG:* "மதுரையில் அயலான் சாதனை" (Fake Location).

2.  **DATE PRECISION (DYNAMIC):**
    - **Specific Dates:** If the input mentions a date (e.g., "Jan 9", "Dec 25"), you **MUST** use that date in the text (e.g., "ஜனவரி 9-ல்").
    - **Relative Terms:** Use "இன்று" (Today) **ONLY IF** no specific date is provided in the input.
    - **Correction:** Do not blindly write "Jan 9" unless the input actually says Jan 9.

3.  **HEADLINE - VIP & ENTITY SPECIFICITY:**
    - **VIPs:** If a Minister/Collector/Actor is named, Headline MUST use their Name (e.g., "அமைச்சர் மா.சு.").
    - **Entities:** Copy Scheme Names exactly (e.g., "Ithu Namma Aattam 2026").
    - **Style:** [Subject/Actor] + [Action Noun]. No Colons.

4.  **YEAR & NUMBER LOCKDOWN:**
    - **Fidelity:** If input says "2023", WRITE "2023". Do not update to 2024/2025.
    - **Exactness:** Keep all figures (Rs 6 Crore, 22,792 buses) exact.

5.  **TONE & LANGUAGE:**
    - **Formal Professional Tamil:** Use "நாளை" (Naalai), NOT "நாளைக்கு".
    - **Fluidity:** Sentences must be complete and grammatically smooth.

**Note:** Output format will be specified at the end of the user message.
***
"""

    TAMIL_NEWS_EDITOR_USER = """
**Raw News Input:**
{raw_content}

**Target Pages:**
{target_pages}

**Instructions:**
- **Location Check:** Is the District mentioned in input? If NO, do not add it.
- **Date Check:** Use the specific date found in text. If none, use 'Indru'.
- **Headline:** Direct Action. No Colons.
"""

    # --------------------------------------------------------------------------
    # RESEARCH & OTHER SERVICE PROMPTS (Preserved)
    # --------------------------------------------------------------------------
    
    # Research Service Prompts
    CITY_RESEARCH_SYSTEM = """You are a city research expert. Provide comprehensive information about cities including demographics, economy, culture, current affairs, and notable issues in markdown format. Output should be in tamil language"""

    CITY_RESEARCH_USER = """Provide detailed information about {city}, including current affairs, demographics, economy, culture, and any notable issues or developments. Keep it informative and factual in markdown format and in tamil language."""

    PERPLEXITY_RESEARCH_SYSTEM = """You are a research assistant focused on current events and real-time information about cities and towns. Output should be in tamil language"""

    PERPLEXITY_RESEARCH_USER = """Research current news, events, issues, and developments related to: {query}. Include recent headlines, local government updates, economic developments, and social issues. Provide factual, up-to-date information in markdown format."""

    # Graph Service Prompts
    KNOWLEDGE_GRAPH_SYSTEM = """You are an expert in knowledge graph creation. Given research data about a city, extract key entities and relationships to create a comprehensive knowledge graph.

Return a JSON object with this exact structure:
{
  "nodes": [
    {
      "id": "unique_id",
      "label": "Display Name",
      "type": "category",
      "description": "Brief description",
      "size": 10
    }
  ],
  "edges": [
    {
      "source": "node_id_1",
      "target": "node_id_2",
      "relationship": "relationship_type",
      "description": "Description of relationship"
    }
  ]
}

Categories should include: city, government, economy, culture, demographics, infrastructure, education, healthcare, tourism, issues, etc.
Create 15-25 nodes and appropriate connecting relationships."""

    KNOWLEDGE_GRAPH_USER = """Create a knowledge graph for {city} based on this research data:

{research_data}"""

    # Social Media Service Prompts
    SOCIAL_HANDLES_SYSTEM = """You are a social media strategist. Generate professional and relevant social media handles for a city based on research data.

Return a JSON object with this exact structure:
{
  "facebook_pages": ["Page Name 1", "Page Name 2"],
  "instagram_pages": ["@handle1", "@handle2"],
  "twitter_accounts": ["@handle1", "@handle2"],
  "whatsapp_group": "Group Name"
}

Make the handles relevant to the city's characteristics, government, or notable features. Maintain a professional tone."""

    SOCIAL_HANDLES_USER = """Generate social media handles for {city} based on this research:

{research_data}"""

    # Content Service Prompts
    HTML_GENERATION_SYSTEM = """You are an expert HTML template generator"""

    HTML_GENERATION_USER = """Create a HTML newscard like the one attached for the below news.  
    Given format is just a reference, do not use any images. 
    Make sure the generated HTML is responsive and mobile friendly for 1080x1080 size. And the entire space should be used for the content. Also the font size should fit properly in the card.
    If it is not a news, use html to create a creative card.
    Use the name "{channel_name}" as the logo name in place of newsit.app
    
    Apply tone-specific styling:
    - Professional: Use formal colors (blues, grays)
    
  Content:
{content}

Sample newscard:
{sample_html}"""

    # Social Media Posts Prompts
    SOCIAL_POSTS_SYSTEM = """You are a social media content creator. Generate professional social media posts for different platforms based on research data about a city.

Return a JSON object with this exact structure:
{
  "instagram_posts": [
    {
      "caption": "Professional Instagram caption",
      "hashtags": ["#hashtag1", "#hashtag2"],
      "type": "carousel/photo/video"
    }
  ],
  "facebook_posts": [
    {
      "content": "Facebook post content",
      "call_to_action": "Read more / Contact"
    }
  ],
  "twitter_posts": [
    {
      "content": "Tweet content (under 280 characters)",
      "hashtags": ["#hashtag1", "#hashtag2"]
    }
  ],
  "linkedin_posts": [
    {
      "content": "Professional LinkedIn post content",
      "tone": "professional/informative"
    }
  ]
}

Create 2-3 posts per platform focusing on news and city highlights. Output should be in tamil language"""

    # News Post Generation Prompts
    NEWS_POST_GENERATION_SYSTEM = """You are a social media content expert specializing in local news and general news. Create engaging, professional posts that drive engagement while maintaining accuracy. Output should be in Tamil."""

    NEWS_POST_GENERATION_USER = """
Transform this news article into an social media post. Do not overuse emojis, drop the user handles etc output should be in tamil (100% professional), try to translate as much as possible to tamil without using other language:

Title: {title}
Content: {content}
Source: {source}
Category: {category}

Requirements:
- Make it professional
- Keep it concise (under 280 characters)
- Maintain factual accuracy
- Use appropriate hashtags for the topic"""

    # Enhanced Research Prompts
    TOPIC_ANALYSIS_SYSTEM = """You are an expert research analyst. Your task is to analyze research topics and break them down into comprehensive research questions and themes.

You should:
1. Identify the main topic and subtopics
2. Break down complex topics into specific research questions
3. Identify relevant knowledge domains and disciplines
4. Suggest different angles of analysis
5. Output structured analysis in markdown format

Focus on being thorough, analytical, and objective.

Output language: Tamil
"""

    TOPIC_ANALYSIS_USER = """Analyze this research topic and provide a comprehensive breakdown:

Topic: {query}

Please provide:
1. **Main Topic Analysis**
   - Core subject matter
   - Key definitions and concepts
   - Scope and boundaries

2. **Subtopic Breakdown**
   - Major themes and areas
   - Specific sub-questions to explore
   - Interconnections between subtopics

3. **Knowledge Domains**
   - Relevant academic disciplines
   - Industry perspectives
   - Historical context needed

4. **Research Questions**
   - Primary research questions
   - Secondary questions for deeper analysis
   - Questions that address different stakeholder perspectives

5. **Analysis Angles**
   - Technical/scientific perspective
   - Economic/business perspective
   - Social/cultural perspective
   - Historical perspective
   - Future implications and trends"""

    MULTI_PERSPECTIVE_SYSTEM = """You are a comprehensive research analyst capable of examining topics from multiple expert perspectives. 

For each research query, provide analysis from these distinct viewpoints:
- Academic/Scientific: Evidence-based research, theories, methodologies
- Industry/Business: Market dynamics, economic factors, commercial implications
- Historical: Past developments, trends, lessons learned
- Social/Cultural: Human impact, societal implications, cultural context
- Critical: Potential problems, limitations, biases, controversies

Each perspective should be substantive, well-reasoned, and based on established knowledge. Address potential biases and provide balanced viewpoints.

Output language: Tamil
"""

    MULTI_PERSPECTIVE_USER = """Provide a comprehensive multi-perspective analysis of: {query}

Structure your response as follows:

## Academic/Scientific Perspective
- Research findings and evidence
- Theoretical frameworks
- Methodologies and approaches
- Current state of knowledge
- Knowledge gaps

## Industry/Business Perspective  
- Market dynamics and trends
- Economic implications
- Business models and strategies
- Competitive landscape
- Commercial opportunities and challenges

## Historical Perspective
- Historical development and evolution
- Key milestones and events
- Past successes and failures
- Lessons learned
- Historical patterns and cycles

## Social/Cultural Perspective
- Human and societal impact
- Cultural considerations
- Ethical implications
- Stakeholder perspectives
- Community effects

## Critical Analysis
- Potential problems and limitations
- Biases and assumptions
- Controversies and debates
- Unintended consequences
- Areas of uncertainty or disagreement

Provide specific examples and evidence where possible. Be objective and acknowledge different viewpoints.
Output language: Tamil"""

    SYNTHESIS_SYSTEM = """You are an expert research synthesizer. Your task is to combine multiple research perspectives into a cohesive, comprehensive analysis.

You should:
1. Identify key themes across all research sources
2. Reconcile conflicting information
3. Highlight the most important insights
4. Create a structured executive summary
5. Identify knowledge gaps and areas for further research
6. Provide actionable conclusions

Output should be structured JSON with clear sections for executive summary, key findings, recommendations, and detailed synthesis.

Output language: Tamil
"""

    SYNTHESIS_USER = """Synthesize the following research findings into a comprehensive analysis:

Research Query: {query}

Research Data:
{research_data}

Please provide a JSON response with the following structure:

{{
  "executive_summary": "2-3 paragraph summary of key findings and insights",
  "key_findings": [
    "Most important finding 1",
    "Most important finding 2",
    "Most important finding 3"
  ],
  "perspectives_synthesis": {{
    "consensus_points": ["Areas where sources agree"],
    "conflicting_views": ["Areas of disagreement or uncertainty"],
    "unique_insights": ["Novel insights from combining perspectives"]
  }},
  "knowledge_gaps": ["Areas needing further research"],
  "recommendations": ["Actionable recommendations based on findings"],
  "bias_assessment": "Assessment of potential biases in the research",
  "confidence_level": "High/Medium/Low confidence in conclusions",
  "detailed_analysis": "Comprehensive synthesis combining all perspectives and findings"
}}

Ensure all sections are filled with substantive content. Be thorough, objective, and highlight both strengths and limitations of the research.

Output language: Tamil
"""

    # --------------------------------------------------------------------------
    # METHODS
    # --------------------------------------------------------------------------

    @classmethod
    def get_city_research_messages(cls, city: str):
        """Get formatted messages for city research"""
        return [
            {"role": "system", "content": cls.CITY_RESEARCH_SYSTEM},
            {"role": "user", "content": cls.CITY_RESEARCH_USER.format(city=city)},
        ]

    @classmethod
    def get_perplexity_research_messages(cls, query: str):
        """Get formatted messages for Perplexity research"""
        return [
            {"role": "system", "content": cls.PERPLEXITY_RESEARCH_SYSTEM},
            {"role": "user", "content": cls.PERPLEXITY_RESEARCH_USER.format(query=query)},
        ]

    @classmethod
    def get_topic_analysis_messages(cls, query: str):
        """Get formatted messages for topic analysis"""
        return [
            {"role": "system", "content": cls.TOPIC_ANALYSIS_SYSTEM},
            {"role": "user", "content": cls.TOPIC_ANALYSIS_USER.format(query=query)},
        ]

    @classmethod
    def get_multi_perspective_messages(cls, query: str):
        """Get formatted messages for multi-perspective analysis"""
        return [
            {"role": "system", "content": cls.MULTI_PERSPECTIVE_SYSTEM},
            {"role": "user", "content": cls.MULTI_PERSPECTIVE_USER.format(query=query)},
        ]

    @classmethod
    def get_synthesis_messages(cls, query: str, research_data: dict):
        """Get formatted messages for research synthesis"""
        # Format research data for the prompt
        data_text = ""
        for key, value in research_data.items():
            if value is not None:
                data_text += f"\n## {key.replace('_', ' ').title()}\n{str(value)}\n"

        return [
            {"role": "system", "content": cls.SYNTHESIS_SYSTEM},
            {
                "role": "user",
                "content": cls.SYNTHESIS_USER.format(query=query, research_data=data_text),
            },
        ]

    @classmethod
    def get_knowledge_graph_messages(cls, city: str, research_data: str):
        """Get formatted messages for knowledge graph generation"""
        return [
            {"role": "system", "content": cls.KNOWLEDGE_GRAPH_SYSTEM},
            {
                "role": "user",
                "content": cls.KNOWLEDGE_GRAPH_USER.format(city=city, research_data=research_data),
            },
        ]

    @classmethod
    def get_social_handles_messages(cls, city: str, research_data: str):
        """Get formatted messages for social handles generation"""
        return [
            {"role": "system", "content": cls.SOCIAL_HANDLES_SYSTEM},
            {
                "role": "user",
                "content": cls.SOCIAL_HANDLES_USER.format(city=city, research_data=research_data),
            },
        ]

    @classmethod
    def get_html_generation_messages(cls, content: str, sample_html: str, channel_name: str = None):
        """Get formatted messages for HTML generation"""
        display_channel_name = channel_name if channel_name else "Social Media Channel"

        return [
            {"role": "system", "content": cls.HTML_GENERATION_SYSTEM},
            {
                "role": "user",
                "content": cls.HTML_GENERATION_USER.format(
                    content=content,
                    sample_html=sample_html,
                    channel_name=display_channel_name,
                ),
            },
        ]

    @classmethod
    def get_social_posts_messages(cls, city: str, research_data: str):
        """Get formatted messages for social media posts generation"""
        return [
            {"role": "system", "content": cls.SOCIAL_POSTS_SYSTEM},
            {
                "role": "user",
                "content": cls.SOCIAL_POSTS_USER.format(city=city, research_data=research_data),
            },
        ]

    @classmethod
    def get_channel_tone_settings(cls, channel_name: str) -> Dict[str, str]:
        """
        Get tone settings for a specific social media channel.

        NOTE: This method is deprecated. Use adapt_content_multi_page_news() for content adaptation.
        Kept for backward compatibility with tests and legacy code.
        """

        # channel_key = channel_name.lower()
        # return cls.CHANNEL_TONE_MAPPING.get(
        #     channel_key,
        #     {
        #         "tone": "professional",
        #         "style": "modern",
        #         "instructions": "Adapt content appropriately for the target audience",
        #     },
        # )
        # Return default settings since CHANNEL_TONE_MAPPING is not used anymore
        # All content adaptation should go through adapt_content_multi_page_news()
        return {
            "tone": "professional",
            "style": "journalistic",
            "instructions": f"Maintain strict professional news standards for {channel_name}",
        }

    @classmethod
    def get_news_post_generation_messages(
        cls, title: str, content: str, source: str, category: str
    ):
        """Get formatted messages for news post generation"""
        return [
            {"role": "system", "content": cls.NEWS_POST_GENERATION_SYSTEM},
            {
                "role": "user",
                "content": cls.NEWS_POST_GENERATION_USER.format(
                    title=title,
                    content=content[:500] + "..." if len(content) > 500 else content,
                    source=source,
                    category=category,
                ),
            },
        ]

    @classmethod
    def get_channel_adaptation_prompt(
        cls, content: str, channel_name: str, custom_instructions: str = "", content_tone: str = "professional"
    ) -> str:
        """Generate channel-specific content adaptation prompt with tone awareness"""
        # Always fetch professional settings regardless of channel_name
        channel_settings = cls.get_channel_tone_settings(channel_name)

        return f"""
        Adapt the following content for {channel_name} with these settings:
        - Tone: Professional
        - Style: Journalistic/Formal
        - Instructions: {channel_settings.get('instructions', '')}
        - Additional instructions: {custom_instructions}

        Original content: {content}

        Return only the adapted content text without any additional formatting or explanations.
        Keep it concise for news card format (max 200 characters).
        """

    @classmethod
    def get_tone_aware_content_prompt(
        cls, content: str, tone: str = "professional", platform: str = None, custom_instructions: str = ""
    ) -> str:
        """Generate tone-aware content generation prompt"""
        tone_info = format_tone_for_prompt("professional") # Force professional

        platform_context = f"for {platform} " if platform else ""

        return f"""
        Create engaging social media content {platform_context}with the following tone characteristics:

        {tone_info}

        Additional Instructions: {custom_instructions}

        Base Content: {content}

        Generate content that:
        1. Matches the professional tone perfectly
        2. Is appropriate for the platform
        3. Maintains the core message

        Return only the final content without explanations.
        Output language: {OUTPUT_LANGUAGE}
        """

    @classmethod
    def get_multi_page_news_messages(cls, raw_content: str, page_list: List[str] = None, accounts: List[Dict] = None, extract_district: bool = False, has_image: bool = False):
        """
        Get formatted messages for Phase 1 Multi-Page Tamil News generation.
        Strict Professional Tone, Character Limits, No Place Names in Headline,
        and strict Noun-ending grammar.
        Works for any list of page names provided dynamically.

        Args:
            raw_content: The raw news content to adapt
            page_list: (Legacy) List of page names as strings
            accounts: (New) List of account dicts with keys: id, name, platform, tone, custom_instructions
                      Format: [{"id": "uuid", "name": "Account Name", "platform": "facebook",
                               "tone": "professional", "custom_instructions": "..."}]
            extract_district: Whether to extract district/city name from content (content-oriented, not account-oriented)
            has_image: Whether an image is provided for vision analysis (repost flow only)

        Returns:
            List of message dicts for LLM API
        """
        # Format the list of pages/accounts into a string for the prompt
        if accounts:
            # New format with account metadata
            formatted_pages = []
            for account in accounts:
                # account_info = f"- {account.get('name', 'Unknown')} (ID: {account.get('id', 'N/A')})"
                account_info = f"- {account.get('name', '').replace(" ", "").lower().strip()}"
                # if account.get('platform'):
                #     account_info += f" [Platform: {account['platform']}]"
                # if account.get('tone') and account['tone'] != 'professional':
                #     account_info += f" [Tone: {account['tone']}]"
                # if account.get('custom_instructions'):
                #     account_info += f"\n  Custom Instructions: {account['custom_instructions']}"
                formatted_pages.append(account_info)
            formatted_pages = "\n".join(formatted_pages)
        elif page_list:
            # Legacy format - just page names
            formatted_pages = "\n".join([f"- {page}" for page in page_list])
        else:
            raise ValueError("Either page_list or accounts must be provided")

        # Build user message with optional district extraction
        user_content = cls.TAMIL_NEWS_EDITOR_USER.format(
            raw_content=raw_content,
            target_pages=formatted_pages
        )

        # Add image analysis instructions if image is provided (repost flow only)
        if has_image:
            user_content = """**IMPORTANT - IMAGE PROVIDED:**

**IMAGE PROCESSING INSTRUCTIONS:**
1. **EXTRACT TEXT FROM IMAGE**: Carefully read and extract ALL text content visible in the image. Ignore graphics, photos, or visual elements
2. **PRIORITIZE IMAGE CONTENT**: Use the text from the image as the PRIMARY source for generating news
3. **COMBINE SOURCES**: If raw content below is also provided, use it as SECONDARY/SUPPLEMENTARY information
4. **ACCURACY**: Do not hallucinate - only use what you can actually see in the image as text content and provided raw text.

""" + user_content

        # Add district extraction instructions if needed (content-oriented, extracted once)
        if extract_district:
            user_content += """

**ADDITIONAL REQUIREMENT - District Extraction:**
- This is CONTENT-ORIENTED, not account-specific.
- Primary Goal: Extract the specific District or Major City name mentioned in the news content. This location is not limited to Tamil Nadu; it can be any district/city (national or international).
- District/City Found: If a specific district or major city is clearly mentioned, return its name in Tamil under the key "District".
- No District/City Found (Scope Determination):
    - If the news content is about a State-level or Regional issue, return the value of District as "is_state_news".
    - Otherwise (if it's about a National-level or International issue), return the value of District as "is_national_news".
- Constraint: The resulting JSON object MUST contain one and only one of the following keys at the top level: "District", "is_state_news", or "is_national_news".
"""

        # Append the appropriate output format at the end
        if extract_district:
            user_content += """

**Output Format:**
CRITICAL: The "Page" field must contain the EXACT account name from the input list above - copy it character-by-character without any spelling changes, transliteration variations, or format modifications. For example, if the input shows "tiruvarurseidhigal", you must use "tiruvarurseidhigal" NOT "thiruvarurseidhigal".

Return the result strictly in this format:
{
    "District": "district/city name in Tamil (e.g., பொன்னேரி, சென்னை)", (or is_state_news, is_national_news)
    "Pages": [
        {"Page": "exact_pagename_from_input",
        "HL": "Direct Headline: Specific Subject + Action", (< 25 chars)
        "Cnt": "Context: Correct Dates, Exact Years, No Fake Locations", (< 250 chars)
        "Tags": "Hashtags"}
    ]
}
"""
        else:
            user_content += """

**Output Format:**
CRITICAL: The "Page" field must contain the EXACT account name from the input list above - copy it character-by-character without any spelling changes, transliteration variations, or format modifications. For example, if the input shows "tiruvarurseidhigal", you must use "tiruvarurseidhigal" NOT "thiruvarurseidhigal".

Return the result strictly in this format:
[
    {"Page": "exact_pagename_from_input",
    "HL": "Direct Headline: Specific Subject + Action", (< 25 chars)
    "Cnt": "Context: Correct Dates, Exact Years, No Fake Locations", (< 250 chars)
    "Tags": "Hashtags"}
]
"""

        return [
            {"role": "system", "content": cls.TAMIL_NEWS_EDITOR_SYSTEM},
            {"role": "user", "content": user_content}
        ]