from agents import function_tool 
import requests
from typing import Dict, Any, List
import json
from dotenv import load_dotenv
import os
import random as rd
import re
from datetime import datetime
from openai import OpenAI

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== HELPER FUNCTIONS =====

def _extract_hashtags(text: str) -> List[str]:
    """Extract all hashtags from text using regex."""
    if not text:
        return []
    hashtags = re.findall(r'#(\w+)', text)
    return list(set(hashtags))  # Remove duplicates

def _convert_timestamp_to_readable(timestamp: int) -> dict:
    """Convert Unix timestamp to readable format and extract posting time insights."""
    if not timestamp:
        return {"error": "No timestamp"}
    
    dt = datetime.fromtimestamp(timestamp)
    hour = dt.hour
    day_of_week = dt.strftime('%A')
    
    # Determine time period
    if 6 <= hour < 12:
        time_period = "Morning (6am-12pm)"
    elif 12 <= hour < 17:
        time_period = "Afternoon (12pm-5pm)"
    elif 17 <= hour < 21:
        time_period = "Evening (5pm-9pm)"
    else:
        time_period = "Night (9pm-6am)"
    
    return {
        "full_datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
        "date": dt.strftime('%Y-%m-%d'),
        "time": dt.strftime('%H:%M:%S'),
        "hour": hour,
        "day_of_week": day_of_week,
        "time_period": time_period,
        "is_weekend": day_of_week in ['Saturday', 'Sunday']
    }

def _extract_key_metrics(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract essential metrics including new features."""
    data = api_response
    
    # Get random 3 comments
    top_comments = []
    edges = data.get("edge_media_to_parent_comment", {}).get("edges", [])
    num_to_sample = min(3, len(edges))
    
    if num_to_sample > 0:
        sampled_edges = rd.sample(edges, num_to_sample)
        for edge in sampled_edges:
            try:
                top_comments.append({
                    "text": edge["node"]["text"],
                    "likes": edge["node"]["edge_liked_by"]["count"],
                    "username": edge["node"]["owner"]["username"]
                })
            except (KeyError, TypeError):
                continue
    
    caption_text = data.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "")
    timestamp = data.get("taken_at_timestamp")
    
    return {
        "post_id": data.get("id"),
        "shortcode": data.get("shortcode"),
        "caption": caption_text[:500],
        "full_caption": caption_text,  # Keep full for hashtag extraction
        "hashtags_used": _extract_hashtags(caption_text),
        "posting_time": _convert_timestamp_to_readable(timestamp) if timestamp else {},
        "media_type": data.get("product_type", "image"),
        "is_video": data.get("is_video", False),
        "likes": data.get("edge_media_preview_like", {}).get("count", 0),
        "comments": data.get("edge_media_to_parent_comment", {}).get("count", 0),
        "video_views": data.get("video_view_count", 0),
        "username": data.get("owner", {}).get("username"),
        "followers": data.get("owner", {}).get("edge_followed_by", {}).get("count", 0),
        "top_comments": top_comments,
        "total_comments_available": len(edges)
    }

def _calculate_engagement_rate(metrics: Dict[str, Any]) -> float:
    """Calculate Engagement Rate."""
    total_engagement = metrics.get("likes", 0) + metrics.get("comments", 0)
    followers = metrics.get("followers", 0)
    return round((total_engagement / followers) * 100, 4) if followers > 0 else 0.0


# ===== TOOL 1: MAIN SCRAPING =====
@function_tool
def analyze_post_metrics(post_shortcode_or_url: str) -> str:
    """Fetches and processes Instagram data with enhanced metrics. Returns JSON string."""
    try:
        shortcode = post_shortcode_or_url
        if "instagram.com" in post_shortcode_or_url:
            shortcode = post_shortcode_or_url.split("/p/")[-1].split("/")[0].split("?")[0]
        
        shortcode = shortcode.strip().rstrip('/')
        
        url = "https://instagram-scraper-stable-api.p.rapidapi.com/get_media_data_v2.php"
        querystring = {"media_code": shortcode}
        headers = {
            "x-rapidapi-key": "53363c208fmsh04bf6e9af78d74cp106543jsna6dd2f3a72fe",
            "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
        }

        print(f"[DEBUG] Fetching data for shortcode: {shortcode}")
        
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code == 403:
            return json.dumps({"error": "API_FORBIDDEN: RapidAPI key invalid or rate limited."})
        elif response.status_code == 404:
            return json.dumps({"error": "POST_NOT_FOUND: Post does not exist or is private."})
        elif response.status_code == 429:
            return json.dumps({"error": "RATE_LIMIT: Too many requests. Wait and try again."})
        
        response.raise_for_status()
        api_response = response.json()
        
        if "error" in api_response:
            return json.dumps({"error": f"API_ERROR: {api_response['error']}"})
        
        if "shortcode" not in api_response:
            return json.dumps({"error": "INVALID_RESPONSE: Missing shortcode field."})
        
        metrics = _extract_key_metrics(api_response)
        
        print(f"[DEBUG] ✅ Successfully extracted metrics for {shortcode}")
        
        return json.dumps(metrics)
        
    except Exception as e:
        return json.dumps({"error": f"UNEXPECTED_ERROR: {str(e)}"})


# ===== TOOL 2: ENGAGEMENT RATE =====
@function_tool
def calculate_post_engagement(post_metrics_json: str) -> float:
    """Calculates Engagement Rate from metrics JSON."""
    try:
        metrics_dict = json.loads(post_metrics_json)
        if 'error' in metrics_dict:
            return 0.0
        return _calculate_engagement_rate(metrics_dict) 
    except Exception:
        return 0.0


# ===== TOOL 3: ADVANCED NLP SENTIMENT ANALYSIS =====
@function_tool
def analyze_content_sentiment_nlp(post_metrics_json: str) -> str:
    """Advanced NLP analysis of caption and comments using AI."""
    try:
        metrics = json.loads(post_metrics_json)
        if 'error' in metrics:
            return json.dumps({"error": metrics['error']})
        
        caption = metrics.get("full_caption", metrics.get("caption", ""))
        comments = metrics.get("top_comments", [])
        
        # Sample up to 5 comments for analysis
        num_to_analyze = min(len(comments), 5)
        sampled_comments = rd.sample(comments, num_to_analyze) if num_to_analyze > 0 else []
        comment_texts = [c["text"] for c in sampled_comments]
        
        # Use AI for deep sentiment analysis
        analysis_prompt = f"""Analyze this Instagram post content:

CAPTION: {caption[:400]}

COMMENTS ({len(comment_texts)} samples):
{chr(10).join(f"- {c}" for c in comment_texts[:5])}

Provide a JSON response with:
1. overall_sentiment: "positive", "negative", or "neutral"
2. key_themes: list of 3-5 main topics/themes mentioned
3. user_frustrations: list of complaints or issues (empty if none)
4. user_desires: list of requests or wishes (empty if none)
5. common_emotions: list of emotions detected (e.g., excitement, curiosity, frustration)
6. engagement_indicators: list of reasons why people are engaging

Return ONLY valid JSON, no markdown."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0,
            max_tokens=600
        )
        
        ai_analysis = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        ai_analysis = re.sub(r'^```json\s*|\s*```$', '', ai_analysis, flags=re.MULTILINE)
        
        # Parse AI response
        try:
            sentiment_data = json.loads(ai_analysis)
        except json.JSONDecodeError:
            sentiment_data = {"error": "AI returned invalid JSON"}
        
        # Combine with basic analysis
        result = {
            "caption_length": len(caption),
            "caption_has_hashtags": "#" in caption,
            "caption_has_emoji": any(ord(c) > 127 for c in caption),
            "caption_has_cta": any(word in caption.lower() for word in ["link", "bio", "shop", "buy", "click", "swipe", "visit", "check", "dm", "follow"]),
            "num_comments_analyzed": len(comment_texts),
            "ai_sentiment_analysis": sentiment_data
        }
        
        return json.dumps(result)
        
    except Exception as e:
        return json.dumps({"error": f"NLP Analysis failed: {str(e)}"})


# ===== TOOL 4: HASHTAG GENERATOR =====
@function_tool
def generate_hashtag_suggestions(post_metrics_json: str, sentiment_json: str) -> str:
    """Generates niche-specific hashtag recommendations using AI."""
    try:
        metrics = json.loads(post_metrics_json)
        sentiment = json.loads(sentiment_json)
        
        if 'error' in metrics:
            return json.dumps({"error": metrics['error']})
        
        caption = metrics.get("full_caption", metrics.get("caption", ""))
        existing_hashtags = metrics.get("hashtags_used", [])
        username = metrics.get("username", "")
        
        # Get themes from sentiment analysis
        themes = sentiment.get("ai_sentiment_analysis", {}).get("key_themes", [])
        
        hashtag_prompt = f"""Generate Instagram hashtags for this post:

USERNAME: @{username}
CAPTION: {caption[:300]}
EXISTING HASHTAGS: {', '.join(f'#{h}' for h in existing_hashtags[:5])}
CONTENT THEMES: {', '.join(themes[:3])}

Generate 10-15 relevant, high-engagement hashtags:
- Mix of popular (100k-1M posts) and niche (10k-100k posts)
- Relevant to content and industry
- Do NOT repeat existing hashtags
- Include trending hashtags if relevant

Return JSON with:
- suggested_hashtags: list of hashtag strings (without #)
- hashtag_strategy: brief explanation of why these hashtags

Return ONLY valid JSON."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": hashtag_prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content.strip()
        ai_response = re.sub(r'^```json\s*|\s*```$', '', ai_response, flags=re.MULTILINE)
        
        try:
            hashtag_data = json.loads(ai_response)
        except json.JSONDecodeError:
            hashtag_data = {
                "suggested_hashtags": [],
                "hashtag_strategy": "AI generation failed",
                "error": "Invalid JSON from AI"
            }
        
        return json.dumps(hashtag_data)
        
    except Exception as e:
        return json.dumps({"error": f"Hashtag generation failed: {str(e)}"})


# ===== TOOL 5: ENHANCED RECOMMENDATIONS =====
@function_tool
def generate_content_recommendations(
    post_metrics_json: str, 
    sentiment_json: str, 
    hashtag_json: str,
    engagement_rate: float
) -> str:
    """Generates comprehensive content strategy report with all insights."""
    try:
        metrics = json.loads(post_metrics_json)
        sentiment = json.loads(sentiment_json)
        hashtags = json.loads(hashtag_json)
        
        if 'error' in metrics:
            return json.dumps({"error": metrics['error']})
        
        posting_time = metrics.get("posting_time", {})
        ai_sentiment = sentiment.get("ai_sentiment_analysis", {})
        
        # Build comprehensive report
        report = {
            "post_performance": {
                "likes": metrics.get("likes", 0),
                "comments": metrics.get("comments", 0),
                "video_views": metrics.get("video_views", 0),
                "engagement_rate": engagement_rate,
                "performance_level": "high" if engagement_rate > 5 else "medium" if engagement_rate > 2 else "low"
            },
            "posting_insights": {
                "posted_at": posting_time.get("full_datetime", "Unknown"),
                "posted_time_period": posting_time.get("time_period", "Unknown"),
                "posted_day": posting_time.get("day_of_week", "Unknown"),
                "is_weekend": posting_time.get("is_weekend", False),
                "optimal_posting_recommendation": ""
            },
            "content_analysis": {
                "media_type": metrics.get("media_type"),
                "caption_quality": "good" if sentiment.get("caption_has_emoji") and sentiment.get("caption_length", 0) > 50 else "needs_improvement",
                "has_call_to_action": sentiment.get("caption_has_cta", False),
                "hashtags_used_count": len(metrics.get("hashtags_used", [])),
                "hashtags_used": metrics.get("hashtags_used", [])
            },
            "sentiment_insights": {
                "overall_sentiment": ai_sentiment.get("overall_sentiment", "neutral"),
                "key_themes": ai_sentiment.get("key_themes", []),
                "user_emotions": ai_sentiment.get("common_emotions", []),
                "user_frustrations": ai_sentiment.get("user_frustrations", []),
                "user_desires": ai_sentiment.get("user_desires", []),
                "engagement_reasons": ai_sentiment.get("engagement_indicators", [])
            },
            "hashtag_recommendations": {
                "suggested_hashtags": hashtags.get("suggested_hashtags", [])[:10],
                "strategy": hashtags.get("hashtag_strategy", "")
            },
            "recommendations": []
        }
        
        # Generate specific recommendations
        recs = report["recommendations"]
        
        # Posting time recommendations
        hour = posting_time.get("hour", 12)
        if hour < 6 or hour > 21:
            recs.append(f"⏰ Post was shared during {posting_time.get('time_period')}. Try posting during peak hours (12-3pm or 7-9pm) for better reach")
            report["posting_insights"]["optimal_posting_recommendation"] = "Post during afternoon or evening hours"
        else:
            recs.append(f"✅ Good posting time ({posting_time.get('time_period')}). Continue posting during this period")
            report["posting_insights"]["optimal_posting_recommendation"] = f"Continue posting during {posting_time.get('time_period')}"
        
        # Engagement recommendations
        if engagement_rate < 3:
            recs.append("📊 Engagement rate is low. Increase audience interaction with questions and polls")
        
        # Hashtag recommendations
        if len(metrics.get("hashtags_used", [])) < 5:
            recs.append(f"#️⃣ Use more hashtags - currently using {len(metrics.get('hashtags_used', []))}. Add 10-15 relevant hashtags")
        
        # Content type recommendations
        if metrics.get("is_video"):
            views_to_likes_ratio = metrics.get("video_views", 0) / max(metrics.get("likes", 1), 1)
            if views_to_likes_ratio > 10:
                recs.append("🎥 Video content has high views but low likes. Add stronger CTA to convert viewers to engagers")
            else:
                recs.append("🎥 Video performs well! Create more Reels and video content")
        
        # CTA recommendations
        if not sentiment.get("caption_has_cta"):
            recs.append("📢 Add clear call-to-action (save this post, share with friends, comment below, link in bio)")
        
        # Sentiment-based recommendations
        if ai_sentiment.get("user_frustrations"):
            recs.append(f"⚠️ Users mentioned frustrations: {', '.join(ai_sentiment.get('user_frustrations', [])[:2])}. Address these in future content")
        
        if ai_sentiment.get("user_desires"):
            recs.append(f"💡 Users want: {', '.join(ai_sentiment.get('user_desires', [])[:2])}. Create content around these topics")
        
        # Caption recommendations
        if sentiment.get("caption_length", 0) < 50:
            recs.append("📝 Write longer, story-driven captions (100-150 words) to increase engagement")
        
        if len(recs) == 0:
            recs.append("🎉 Excellent post performance! Maintain this content quality and strategy")
        
        return json.dumps(report, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Report generation failed: {str(e)}"})