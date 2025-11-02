# Agents/SentimentAnalysis.py (ENHANCED VERSION)

from agents import ModelSettings, Agent
from Tools.Instagram_Tools import (
    analyze_content_sentiment_nlp,
    generate_hashtag_suggestions,
    generate_content_recommendations
)

INSTRUCTIONS = """ 
You are an Advanced Content Analysis Agent for Instagram posts.

**INPUT:** JSON with "metrics_json" and "engagement_rate"

**YOUR EXACT STEPS:**
1. Parse input to extract metrics_json and engagement_rate
2. Call 'analyze_content_sentiment_nlp' with metrics_json → get sentiment_json
3. Call 'generate_hashtag_suggestions' with metrics_json and sentiment_json → get hashtag_json
4. Call 'generate_content_recommendations' with metrics_json, sentiment_json, hashtag_json, and engagement_rate
5. Output ONLY the final JSON report from step 4

**CRITICAL RULES:**
- NO explanations, NO markdown, NO commentary
- Just output the pure JSON from generate_content_recommendations
- Do NOT add any text before or after the JSON
- The JSON must be parseable by json.loads()

**Example Output Structure:**
{
  "post_performance": {...},
  "posting_insights": {...},
  "content_analysis": {...},
  "sentiment_insights": {...},
  "hashtag_recommendations": {...},
  "recommendations": [...]
}
"""

model = "gpt-4o-mini"

final_report_agent = Agent(
    name="Advanced Content Analyzer",
    model=model,
    instructions=INSTRUCTIONS,
    model_settings=ModelSettings(
        tool_choice="required",
        temperature=0,
        parallel_tool_calls=False,
        max_tokens=3000  # Increased for detailed reports
    ),
    tools=[
        analyze_content_sentiment_nlp,
        generate_hashtag_suggestions,
        generate_content_recommendations
    ]
)