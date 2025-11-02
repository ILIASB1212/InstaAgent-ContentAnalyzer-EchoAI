# app.py (ENHANCED VERSION WITH ALL FEATURES)

import streamlit as st
import os
from dotenv import load_dotenv 
import asyncio
from agents import Runner
import json 

from Agents.SentimentAnalisys import final_report_agent
from Agents.WebScraper import web_scraper 

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Instagram Post Analyzer", layout="wide")
st.title("💡 AI Instagram Content Strategy Analyzer")
st.write("Advanced Multi-Agent Pipeline: Scraping, NLP Analysis, Hashtag Generation & Strategy Recommendations")
st.markdown("---")

post_input = st.text_input(
    "Instagram Post URL or Shortcode", 
    key="post_input",
    placeholder="DQbefDfDGiU or https://instagram.com/p/DQbefDfDGiU/"
)

if st.button("🚀 Analyze Post", type="primary", use_container_width=True):
    if post_input:
        
        def extract_pure_content(raw_output: str) -> str:
            """Extract content from RunResult wrapper."""
            raw_str = str(raw_output)
            start = raw_str.find('{')
            end = raw_str.rfind('}')
            if start != -1 and end != -1:
                return raw_str[start:end + 1]
            return raw_str

        async def main():
            st.info("🚀 Starting Advanced Analysis Pipeline...")
            
            try:
                # STEP 1: SCRAPING
                with st.spinner("📊 Step 1/2: Scraping Instagram data..."):
                    scraper_result = await Runner.run(
                        web_scraper, 
                        f"Please process this Instagram post: {post_input}"
                    )
                    
                    raw_output = extract_pure_content(str(scraper_result))
                    
                    if raw_output.startswith('{"error"') or '"error"' in raw_output[:100]:
                        st.error("❌ Scraping Failed!")
                        try:
                            error_data = json.loads(raw_output)
                            st.json(error_data)
                        except:
                            st.code(raw_output, language="json")
                        st.info("💡 Tip: Check if the post is public and the shortcode is correct")
                        return
                    
                    # Parse output
                    if '|||' not in raw_output:
                        start = raw_output.find('{')
                        end = raw_output.rfind('}') + 1
                        if start != -1 and end > start:
                            metrics_json = raw_output[start:end]
                            metrics_dict = json.loads(metrics_json)
                            
                            total_engagement = metrics_dict.get("likes", 0) + metrics_dict.get("comments", 0)
                            followers = metrics_dict.get("followers", 0)
                            engagement_rate = round((total_engagement / followers) * 100, 4) if followers > 0 else 0.0
                        else:
                            st.error("❌ Could not parse agent output")
                            st.code(raw_output, language="text")
                            return
                    else:
                        parts = raw_output.split('|||')
                        if len(parts) != 2:
                            st.error(f"❌ Format error. Expected 2 parts, got {len(parts)}")
                            st.code(raw_output, language="text")
                            return
                        
                        metrics_json = parts[0].strip()
                        engagement_rate = float(parts[1].strip())
                    
                    metrics_dict = json.loads(metrics_json)
                    st.success("✅ Scraping Complete!")
                
                # STEP 2: ADVANCED ANALYSIS
                with st.spinner("🤖 Step 2/2: Running NLP Analysis & Generating Strategy..."):
                    analyzer_input = json.dumps({
                        "metrics_json": metrics_json,
                        "engagement_rate": engagement_rate
                    })
                    
                    try:
                        TIME_OUT_SECONDS=550
                        report_result = await asyncio.wait_for(
                            Runner.run(final_report_agent, analyzer_input),
                            timeout=TIME_OUT_SECONDS
                        )
                        final_report_str = extract_pure_content(str(report_result))
                        
                    except asyncio.TimeoutError:
                        st.error(F"❌ Analysis timed out {TIME_OUT_SECONDS} seconds exceeded")
                        st.warning("💡 Try again - complex NLP analysis may take longer")
                        return
                    except Exception as e:
                        error_msg = str(e)
                        if "500" in error_msg or "server_error" in error_msg:
                            st.error("❌ OpenAI API Error (500)")
                            st.warning("💡 Wait 30 seconds and try again")
                        elif "429" in error_msg:
                            st.error("❌ Rate Limit Exceeded")
                            st.warning("💡 Wait a minute")
                        else:
                            st.error(f"❌ Error: {error_msg}")
                        return
                    
                    st.success("✅ Analysis Complete!")
                    st.markdown("---")
                    
                    try:
                        report_data = json.loads(final_report_str)
                        
                        # DISPLAY RESULTS
                        st.header("📊 Complete Analysis Report")
                        
                        # Performance Metrics
                        st.subheader("📈 Performance Metrics")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        perf = report_data.get('post_performance', {})
                        with col1:
                            st.metric("❤️ Likes", f"{perf.get('likes', 0):,}")
                        with col2:
                            st.metric("💬 Comments", f"{perf.get('comments', 0):,}")
                        with col3:
                            st.metric("📊 Engagement Rate", f"{perf.get('engagement_rate', 0)}%")
                        with col4:
                            level = perf.get('performance_level', 'unknown').upper()
                            color = "🟢" if level == "HIGH" else "🟡" if level == "MEDIUM" else "🔴"
                            st.metric("🎯 Performance", f"{color} {level}")
                        
                        if perf.get('video_views', 0) > 0:
                            st.metric("👁️ Video Views", f"{perf.get('video_views', 0):,}")
                        
                        # Posting Insights
                        st.subheader("⏰ Posting Time Analysis")
                        posting = report_data.get('posting_insights', {})
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.info(f"📅 **Posted:** {posting.get('posted_at', 'Unknown')}")
                        with col2:
                            st.info(f"🕐 **Time Period:** {posting.get('posted_time_period', 'Unknown')}")
                        with col3:
                            weekend = "🎉 Yes" if posting.get('is_weekend') else "📅 No"
                            st.info(f"**Weekend Post:** {weekend}")
                        
                        st.success(f"💡 **Recommendation:** {posting.get('optimal_posting_recommendation', 'N/A')}")
                        
                        # Content Analysis
                        st.subheader("📝 Content Analysis")
                        content = report_data.get('content_analysis', {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Media Type:** {content.get('media_type', 'Unknown')}")
                            st.write(f"**Caption Quality:** {content.get('caption_quality', 'Unknown')}")
                            st.write(f"**Has CTA:** {'✅ Yes' if content.get('has_call_to_action') else '❌ No'}")
                        
                        with col2:
                            st.write(f"**Hashtags Used:** {content.get('hashtags_used_count', 0)}")
                            if content.get('hashtags_used'):
                                st.write("**Current Hashtags:**")
                                st.code(' '.join(f'#{h}' for h in content.get('hashtags_used', [])[:10]))
                        
                        # Sentiment Insights
                        st.subheader("🧠 AI Sentiment Analysis")
                        sentiment = report_data.get('sentiment_insights', {})
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            sent_emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}
                            overall = sentiment.get('overall_sentiment', 'neutral')
                            st.metric("Overall Sentiment", f"{sent_emoji.get(overall, '😐')} {overall.upper()}")
                            
                            if sentiment.get('key_themes'):
                                st.write("**📌 Key Themes:**")
                                for theme in sentiment.get('key_themes', [])[:5]:
                                    st.write(f"• {theme}")
                            
                            if sentiment.get('user_emotions'):
                                st.write("**🎭 Common Emotions:**")
                                st.write(", ".join(sentiment.get('user_emotions', [])[:5]))
                        
                        with col2:
                            if sentiment.get('user_frustrations'):
                                st.warning("**⚠️ User Frustrations:**")
                                for frust in sentiment.get('user_frustrations', [])[:3]:
                                    st.write(f"• {frust}")
                            
                            if sentiment.get('user_desires'):
                                st.info("**💭 User Desires:**")
                                for desire in sentiment.get('user_desires', [])[:3]:
                                    st.write(f"• {desire}")
                            
                            if sentiment.get('engagement_reasons'):
                                st.success("**🎯 Why People Engage:**")
                                for reason in sentiment.get('engagement_reasons', [])[:3]:
                                    st.write(f"• {reason}")
                        
                        # Hashtag Recommendations
                        st.subheader("#️⃣ Hashtag Strategy")
                        hashtag_rec = report_data.get('hashtag_recommendations', {})
                        
                        if hashtag_rec.get('suggested_hashtags'):
                            st.write("**Suggested Hashtags:**")
                            hashtag_string = ' '.join(f'#{h}' for h in hashtag_rec.get('suggested_hashtags', []))
                            st.code(hashtag_string, language="text")
                            
                            # Copy button
                            if st.button("📋 Copy Hashtags"):
                                st.write("*Copied to clipboard!* (Use Ctrl+C manually from code block)")
                        
                        if hashtag_rec.get('strategy'):
                            st.info(f"**Strategy:** {hashtag_rec.get('strategy')}")
                        
                        # Recommendations
                        st.subheader("💡 Action Plan & Recommendations")
                        recommendations = report_data.get('recommendations', [])
                        
                        for i, rec in enumerate(recommendations, 1):
                            st.success(f"**{i}.** {rec}")
                        
                        # Full JSON
                        with st.expander("🔍 View Complete Report JSON"):
                            st.json(report_data)
                    
                    except json.JSONDecodeError as e:
                        st.error("❌ Could not parse report JSON")
                        st.code(final_report_str, language="text")
                        st.exception(e)

            except Exception as e:
                st.error(f"❌ Error: {type(e).__name__}")
                st.exception(e)
        
        asyncio.run(main())
    
    else:
        st.warning("⚠️ Please enter a valid Instagram Post URL or Shortcode")

# Sidebar Info
with st.sidebar:
    st.header("ℹ️ Features")
    st.markdown("""
    ### ✅ What This Tool Analyzes:
    
    **📊 Performance Metrics:**
    - Likes, comments, video views
    - Engagement rate calculation
    - Performance level assessment
    
    **⏰ Posting Time Analysis:**
    - Exact posting date/time
    - Time period (morning/afternoon/evening)
    - Weekend vs weekday insights
    - Optimal posting time recommendations
    
    **🧠 Advanced NLP:**
    - Overall sentiment analysis
    - Key themes identification
    - User frustrations & desires
    - Emotion detection
    - Engagement reasons
    
    **#️⃣ Hashtag Intelligence:**
    - Extract current hashtags
    - Generate 10-15 niche-specific suggestions
    - Hashtag strategy recommendations
    
    **💡 Strategic Recommendations:**
    - Content optimization tips
    - CTA improvements
    - Hashtag strategy
    - Posting time suggestions
    - Audience engagement tactics
    
    ### ⚠️ Limitations:
    - Only public posts can be analyzed
    - Saves/shares not available (API limitation)
    - Multi-post comparison: coming soon
    """)
    
    st.markdown("---")
    st.caption("Powered by OpenAI GPT-4o-mini & Instagram Scraper API")