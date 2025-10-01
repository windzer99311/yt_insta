# gui.py
import streamlit as st
import asyncio
import re,os
from pytubefix.exceptions import RegexMatchError

from optimizer import video_metadata, file_stream_data
from merge import combine_chunks, merge_video_audio
from download import main  # Updated main() now accepts progress_cb

st.set_page_config(page_title="YouTube Downloader", layout="centered")
st.title("🎬 YouTube Video Downloader & Merger")

# URL input
url = st.text_input("Enter YouTube video URL:")

if url:
    try:
        # Load and cache video metadata once per URL
        if 'video_info' not in st.session_state or st.session_state.get('cached_url') != url:
            st.session_state.video_info = video_metadata(url)
            st.session_state.cached_url = url
            st.session_state.quality_selected = "Select quality:"

        video_info = st.session_state.video_info
        video_title = video_info['video_title']
        video_duration = video_info['video_duration']
        video_thumbnail = video_info['video_thumbnail']
        quality_options = ['Select quality:'] + video_info['quality_option']
        quality_selected_map = video_info['quality_selected']

        st.image(video_thumbnail, width=300)
        st.subheader(video_title)
        st.caption(f"Duration: {video_duration}")

        # Dropdown with session-state tracking
        selected_quality_label = st.selectbox(
            "Choose Quality:", quality_options,
            index=quality_options.index(st.session_state.quality_selected)
        )

        # Save selection persistently
        if selected_quality_label != "Select quality:":
            st.session_state.quality_selected = selected_quality_label

            st.info("🔍 Getting stream URLs...")
            quality_code = quality_selected_map[selected_quality_label]
            video_data = file_stream_data(url, quality_code)

            video_stream = video_data['video_streaming_url']
            audio_stream = video_data['audio_streaming_url']
            video_size = video_data['video_size']
            audio_size = video_data['audio_size']

            if st.button("⬇ Download and Merge"):
                with st.spinner("⏳ Downloading and merging, please wait..."):
                    progress_bar = st.progress(0, text="⬇ Downloading...")

                    def update_combined_bar(progress):
                        progress_bar.progress(progress, text=f"⬇ Downloading... {int(progress * 100)}%")

                    asyncio.run(main(
                        video_stream, audio_stream, video_size, audio_size,
                        progress_cb=update_combined_bar
                    ))

                    safe_title = "test"
                    video_file = combine_chunks("mp4")
                    audio_file = combine_chunks("m4a")
                    
                    save_video = st.download_button(
                    label="💾 Save Video",
                    data=video_file,
                    file_name=f"{safe_title}.mp4",
                    mime="video/mp4"
                )
                   
                if os.path.exists(f'{safe_title}.mp4'):
                    os.remove(f'{safe_title}.mp4')
    except RegexMatchError:
        st.error("❌ Invalid YouTube URL. Please check and try again.")
    except Exception as e:
        st.error(f"⚠ Unexpected error: {e}")

