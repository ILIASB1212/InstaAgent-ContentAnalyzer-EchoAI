# Agents/WebScraper.py (FIXED VERSION)

from agents import ModelSettings, Agent
from Tools.Instagram_Tools import analyze_post_metrics, calculate_post_engagement
from dotenv import load_dotenv
import os

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

INSTRUCTIONS = """ 
You are a Web Scraping and Metrics Agent.

**YOUR TASK:**
1. Call 'analyze_post_metrics' with the post shortcode/URL provided by the user
2. If it returns an error JSON (contains "error" key), stop and output ONLY that error JSON
3. If successful, call 'calculate_post_engagement' passing the exact JSON string from step 1
4. Your FINAL response must be EXACTLY: <metrics_json_from_step1>|||<float_from_step2>

**CRITICAL OUTPUT FORMAT:**
- No explanations, no commentary
- No markdown, no code blocks
- Just: {"post_id":"...","likes":500,...}|||3.45
- The ||| separator is REQUIRED
- Do NOT add spaces around |||

**Example Success:**
{"post_id":"123","shortcode":"ABC","likes":500,"comments":20,"followers":10000}|||5.2

**Example Error:**
{"error":"POST_NOT_FOUND: Post does not exist or is private."}
"""

model = "gpt-4o-mini"

web_scraper = Agent(
    name="Web Scraper Agent",
    model=model,
    instructions=INSTRUCTIONS,
    model_settings=ModelSettings(
        tool_choice="required",  # Force tool usage
        temperature=0,
        parallel_tool_calls=False  # Sequential execution
    ),
    tools=[
        analyze_post_metrics,
        calculate_post_engagement
    ]
)