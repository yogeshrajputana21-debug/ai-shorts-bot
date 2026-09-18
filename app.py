import streamlit as st
import asyncio
import os
import engine

st.set_page_config(page_title="AI Shorts Automation", page_icon="⚡", layout="wide")

st.title("⚡ AI Shorts Creator & Auto-Poster")
st.markdown("Automated pipeline: **Google Trends ➔ Gemini ➔ Edge-TTS ➔ Whisper Subtitles ➔ Pexels ➔ FFmpeg**")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Trend Detection & Scripting")
    region = st.selectbox("Trends Region", ["US", "IN", "GB", "CA", "AU"])
    
    if st.button("🔍 Scan Trending Topics"):
        with st.spinner("Fetching latest RSS topics..."):
            st.session_state["trends"] = engine.fetch_top_trends(region)

    trends = st.session_state.get("trends", engine.fetch_top_trends(region))
    selected_trend = st.selectbox("Select Topic or Enter Custom:", trends)
    custom_topic = st.text_input("Or custom topic:", value=selected_trend)

    if st.button("✍️ Generate Script"):
        with st.spinner("Generating viral script..."):
            script = engine.generate_script(custom_topic)
            st.session_state["script"] = script

    script_text = st.text_area("Script (editable):", value=st.session_state.get("script", ""), height=120)

    st.subheader("2. Build Video")
    broll_query = st.text_input("B-Roll Visual Keyword:", value="neon cyberpunk technology")
    
    if st.button("🚀 Render 9:16 Short"):
        if not script_text:
            st.error("Please generate or enter a script first!")
        else:
            with st.status("Assembling video pipeline...", expanded=True) as status:
                st.write("🎙️ Generating Edge-TTS audio...")
                asyncio.run(engine.create_voiceover(script_text))
                
                st.write("📝 Transcribing subtitles with Whisper...")
                engine.generate_subtitles_ass()
                
                st.write("📹 Fetching 1080x1920 video clip...")
                engine.fetch_background_video(query=broll_query)
                
                st.write("🎞️ Rendering and burning subtitles via FFmpeg...")
                engine.render_video_ffmpeg()
                
                status.update(label="Render Completed Successfully!", state="complete")
                st.session_state["rendered"] = True

with col2:
    st.subheader("3. Video Preview & Download")
    if os.path.exists("final_short.mp4"):
        st.video("final_short.mp4")
        with open("final_short.mp4", "rb") as f:
            st.download_button(
                label="📥 Download Video (for manual upload/checking)",
                data=f,
                file_name="trending_short.mp4",
                mime="video/mp4"
            )
    else:
        st.info("Render a video on the left panel to see the live preview here.")
