import streamlit as st
import os
import sys
import subprocess
import tempfile
import time
import re
from datetime import datetime
from pytubefix import YouTube
from utils import download_instagram_video, is_valid_instagram_url, get_shortcode_from_url

# Add current directory to path for imports
sys.path.append(os.getcwd())

# Set page configuration
st.set_page_config(
    page_title="Video Downloader - YouTube & Instagram",
    page_icon="🎬",
    layout="centered"
)

# Load external CSS
if os.path.exists('styles.css'):
    with open('styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Override Streamlit's default text colors for better compatibility
st.markdown("""
    <style>
    .stAlert p {
        color: #000000 !important;
    }
    .streamlit-expanderHeader {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# App header with attractive styling
st.markdown('<h1 class="app-title">Video Downloader</h1>', unsafe_allow_html=True)
st.markdown('<p class="app-subtitle">Download videos from YouTube and Instagram with ease</p>', unsafe_allow_html=True)

# Create main navigation tabs
tab1, tab2 = st.tabs(["🎬 YouTube", "📹 Instagram"])

with tab1:
    # YouTube Downloader Tab
    st.header("Download YouTube Videos")
    st.markdown("Enter a YouTube URL to download the video")
    
    # Initialize YouTube session state
    if 'yt_file_ready_for_download' not in st.session_state:
        st.session_state.yt_file_ready_for_download = False
        st.session_state.yt_download_file_path = None
        st.session_state.yt_download_file_name = None
        st.session_state.yt_video_file_path = None
        st.session_state.yt_audio_file_path = None
        st.session_state.yt_file_downloaded = False

    # Function to delete YouTube server files
    def delete_yt_server_files():
        """Delete downloaded files from the server after client has downloaded them"""
        files_to_delete = [
            st.session_state.yt_download_file_path,
            st.session_state.yt_video_file_path,
            st.session_state.yt_audio_file_path
        ]

        for file_path in files_to_delete:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {str(e)}")

        # Reset session state
        st.session_state.yt_file_ready_for_download = False
        st.session_state.yt_download_file_path = None
        st.session_state.yt_download_file_name = None
        st.session_state.yt_video_file_path = None
        st.session_state.yt_audio_file_path = None
        st.session_state.yt_file_downloaded = True

    # Function to format file size
    def format_size(bytes_size):
        """Convert bytes to human-readable format"""
        if bytes_size is None:
            return "Unknown size"

        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} GB"

    # Function to get video details
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_video_info(url):
        """Extract video information from YouTube URL"""
        try:
            yt = YouTube(url)

            # Get basic video info
            title = yt.title
            thumbnail = yt.thumbnail_url
            duration = time.strftime('%H:%M:%S', time.gmtime(yt.length))

            # Get available video streams
            video_streams = {}
            for stream in yt.streams.filter(progressive=False):
                if stream.resolution:
                    res = stream.resolution
                    fps = stream.fps
                    size_bytes = stream.filesize

                    # Get the best quality stream for each resolution
                    if res not in video_streams or video_streams[res]['fps'] < fps:
                        video_streams[res] = {
                            'fps': fps,
                            'size': format_size(size_bytes),
                            'size_bytes': size_bytes,
                            'stream': stream
                        }

            # Sort by resolution (highest first)
            sorted_streams = sorted(video_streams.items(),
                                    key=lambda x: int(x[0][:-1]) if x[0][:-1].isdigit() else 0,
                                    reverse=True)

            # Always get the first audio stream with lowest bitrate
            audio_stream = yt.streams.filter(only_audio=True).order_by('bitrate').asc().first()

            return {
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'video_streams': sorted_streams,
                'audio_stream': audio_stream,
                'yt': yt
            }
        except Exception as e:
            st.error(f"Error retrieving video information: {str(e)}")
            return None

    # Function to download YouTube video
    def download_youtube_video(video_url, audio_url, title, threads=32):
        """Use download.py to download the video with customizable parameters"""
        try:
            # Create a safe filename from the title
            safe_title = "".join([c if c.isalnum() or c in [' ', '.', '_', '-'] else '_' for c in title])
            safe_title = safe_title.strip().replace(' ', '_')

            # Set output filenames based on the title
            video_output = f"{safe_title}.mp4"
            audio_output = f"{safe_title}.m4a"

            # Create a modified version of download.py with the new URLs and parameters
            old_file = "download.py"

            with open(old_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace URLs and other settings in the content
            content = content.replace("VIDEO_URL =", f"VIDEO_URL =\"{video_url}\"  #")
            content = content.replace("AUDIO_URL =", f"AUDIO_URL =\"{audio_url}\"  #")
            content = content.replace("THREADS =", f"THREADS = {threads}  #")
            content = content.replace("VIDEO_OUTPUT =", f"VIDEO_OUTPUT = \"{video_output}\"  #")
            content = content.replace("AUDIO_OUTPUT =", f"AUDIO_OUTPUT = \"{audio_output}\"  #")
            
            # Create a modified file in the current directory
            temp_path = "update_download.py"
            with open(temp_path, 'w', encoding="utf-8") as f:
                f.write(content)

            # Run the modified script and capture output
            process = subprocess.Popen(
                [f"{sys.executable}", temp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )

            # Create a single progress placeholder that will be updated
            progress_placeholder = st.empty()

            # Initialize variables for tracking progress
            output_text = ""
            last_video_progress = 0
            last_audio_progress = 0
            video_speed = "0 B/s"
            audio_speed = "0 B/s"
            video_eta = "Calculating..."
            audio_eta = "Calculating..."
            combined_progress = 0
            status_text = "Preparing download..."

            # Display initial progress
            with progress_placeholder.container():
                st.write("Download Progress:")
                st.progress(0)
                st.write(status_text)

            # Read the output line by line
            for line in process.stdout:
                output_text += line

                # Check for Video progress
                video_match = re.search(r'Video: \[.*?\] (\d+\.\d+)% at (.*?)/s ETA: (.*?)(?:\n|$)', line)
                if video_match:
                    video_percent = float(video_match.group(1))
                    video_speed = video_match.group(2)
                    video_eta = video_match.group(3)

                    # Store video progress
                    last_video_progress = video_percent / 100

                    # Update combined progress (video is 60% of total, audio is 40%)
                    combined_progress = (last_video_progress * 0.6) + (last_audio_progress * 0.4)

                    # Calculate overall percentage
                    overall_percent = combined_progress * 100

                    # Update combined status text
                    status_text = f"Overall: {overall_percent:.1f}% | Video: {video_percent:.1f}% at {video_speed}/s"
                    if last_audio_progress > 0:
                        status_text += f" | Audio: {last_audio_progress * 100:.1f}% at {audio_speed}/s"

                    # Update progress display
                    with progress_placeholder.container():
                        st.write("Download Progress:")
                        st.progress(combined_progress)
                        st.write(status_text)

                # Check for Audio progress
                audio_match = re.search(r'Audio: \[.*?\] (\d+\.\d+)% at (.*?)/s ETA: (.*?)(?:\n|$)', line)
                if audio_match:
                    audio_percent = float(audio_match.group(1))
                    audio_speed = audio_match.group(2)
                    audio_eta = audio_match.group(3)

                    # Store audio progress
                    last_audio_progress = audio_percent / 100

                    # Update combined progress (video is 60% of total, audio is 40%)
                    combined_progress = (last_video_progress * 0.6) + (last_audio_progress * 0.4)

                    # Calculate overall percentage
                    overall_percent = combined_progress * 100

                    # Update combined status text
                    status_text = f"Overall: {overall_percent:.1f}% | Video: {last_video_progress * 100:.1f}% at {video_speed}/s"
                    status_text += f" | Audio: {audio_percent:.1f}% at {audio_speed}/s"

                    # Update progress display
                    with progress_placeholder.container():
                        st.write("Download Progress:")
                        st.progress(combined_progress)
                        st.write(status_text)

            # Wait for the process to complete
            process.wait()

            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass

            if process.returncode == 0:
                # Set progress bar to 100% on successful completion
                with progress_placeholder.container():
                    st.write("Download Progress:")
                    st.progress(1.0)
                    st.write("Download completed! Processing final file...")

                # Prepare the final video for download
                video_path = os.path.abspath(video_output)
                audio_path = os.path.abspath(audio_output)
                final_path = os.path.abspath(
                    f"{os.path.splitext(video_output)[0]}_video{os.path.splitext(video_output)[1]}")
                file_name = os.path.basename(final_path)

                # Set up the session state for auto-download and file cleanup
                st.session_state.yt_file_ready_for_download = True
                st.session_state.yt_download_file_path = final_path
                st.session_state.yt_download_file_name = file_name
                st.session_state.yt_video_file_path = video_path
                st.session_state.yt_audio_file_path = audio_path

                # Success message
                st.success("Download completed! Video will begin downloading automatically.")

                # Function to mark download as complete and trigger cleanup
                def on_download_complete():
                    st.session_state.yt_file_downloaded = True
                    delete_yt_server_files()

                # Auto-download file to the browser
                with open(final_path, "rb") as file:
                    download_btn = st.download_button(
                        label="Download Video to Your Device",
                        data=file,
                        file_name=file_name,
                        mime="video/mp4",
                        key="yt_auto_download_btn",
                        use_container_width=True,
                        help="Click to download the video if it doesn't start automatically",
                        on_click=on_download_complete
                    )

                return True
            else:
                st.error("Download failed. Check the logs for details.")
                return False

        except Exception as e:
            st.error(f"Error during download: {str(e)}")
            return False

    # Check if there's a YouTube file ready for auto-download from previous run
    if st.session_state.yt_file_ready_for_download and st.session_state.yt_download_file_path and os.path.exists(
            st.session_state.yt_download_file_path):
        auto_download_container = st.container()
        with auto_download_container:
            file_path = st.session_state.yt_download_file_path
            file_name = st.session_state.yt_download_file_name

            st.success("Your video is ready! Downloading now...")

            # Create a function to trigger cleanup after download
            def on_persistent_download_complete():
                st.session_state.yt_file_downloaded = True
                delete_yt_server_files()

            with open(file_path, "rb") as file:
                st.download_button(
                    label="Download Video to Your Device",
                    data=file,
                    file_name=file_name,
                    mime="video/mp4",
                    key="yt_persistent_download_btn",
                    use_container_width=True,
                    on_click=on_persistent_download_complete
                )

    # YouTube URL input
    yt_url = st.text_input("YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

    if yt_url:
        # Get video info
        video_info = get_video_info(yt_url)

        if video_info:
            # Display video info
            col1, col2 = st.columns([1, 2])

            with col1:
                st.image(video_info['thumbnail'], use_container_width=True)

            with col2:
                st.subheader(video_info['title'])
                st.write(f"**Duration:** {video_info['duration']}")

                # Quality selection
                if video_info['video_streams']:
                    quality_options = []
                    for resolution, info in video_info['video_streams']:
                        quality_options.append(f"{resolution} ({info['fps']}fps) - {info['size']}")

                    selected_quality = st.selectbox(
                        "Select Quality:",
                        quality_options,
                        index=0
                    )

                    # Thread selection
                    threads = st.slider("Download Threads:", min_value=1, max_value=64, value=32)

                    # Download button
                    if st.button("Download Video", type="primary", use_container_width=True):
                        # Get selected stream
                        selected_index = quality_options.index(selected_quality)
                        selected_stream = video_info['video_streams'][selected_index][1]['stream']

                        # Get URLs
                        video_url = selected_stream.url
                        audio_url = video_info['audio_stream'].url if video_info['audio_stream'] else None

                        if audio_url:
                            download_youtube_video(video_url, audio_url, video_info['title'], threads)
                        else:
                            st.error("No audio stream available for this video.")
                else:
                    st.error("No video streams available for this video.")

with tab2:
    # Instagram Downloader Tab
    st.header("Download Instagram Videos")
    
    # Initialize Instagram session state for download history
    if 'ig_download_history' not in st.session_state:
        st.session_state.ig_download_history = []

    # Instructions
    st.markdown("""
    ### How to use:
    1. Paste an Instagram video URL (post or reel) below
    2. Click the Download button
    3. Preview the video and download it to your device
    """)

    # Input field for Instagram URL
    url_container = st.container()
    with url_container:
        instagram_url = st.text_input(
            "Enter Instagram Video URL:",
            placeholder="https://www.instagram.com/p/...",
            label_visibility="visible"
        )

    # Create containers for status and video
    status_container = st.empty()
    video_container = st.empty()
    download_container = st.empty()

    # Download button
    if st.button("Download Instagram Video", type="primary"):
        if not instagram_url:
            status_container.error("Please enter an Instagram URL.")
        elif not is_valid_instagram_url(instagram_url):
            status_container.error("Invalid Instagram URL. Please enter a valid Instagram post or reel URL.")
        else:
            # Show processing message
            status_container.info("Processing... Please wait.")

            try:
                # Download the video
                video_path = download_instagram_video(instagram_url)

                if video_path:
                    # Display success message
                    status_container.success("Video downloaded successfully!")

                    # Add to download history
                    shortcode = get_shortcode_from_url(instagram_url)
                    st.session_state.ig_download_history.append({
                        "url": instagram_url,
                        "shortcode": shortcode,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "file_path": video_path
                    })

                    # Read the video file once
                    with open(video_path, "rb") as video_file:
                        video_bytes = video_file.read()

                    # Clear previous display
                    video_container.empty()

                    # Use a horizontal layout with the video and download button side by side
                    cols = video_container.columns([3, 2])

                    # Display video in the left column with proper frame
                    with cols[0]:
                        st.markdown('<div style="border:1px solid #ddd; border-radius:5px; padding:10px; background-color:#f0f0f0;">', unsafe_allow_html=True)
                        st.video(video_bytes)
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Add styled download button in the right column
                    with cols[1]:
                        st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)  # Add some spacing for alignment
                        st.download_button(
                            label="Download Video",
                            data=video_bytes,
                            file_name=os.path.basename(video_path),
                            mime="video/mp4",
                            key="ig_video_download",
                            use_container_width=True
                        )

                        # Add file info
                        file_size = round(len(video_bytes) / (1024 * 1024), 2)  # Size in MB
                        st.markdown(f"<div style='padding:5px; margin-top:5px;'><strong>Size:</strong> {file_size} MB<br><strong>Format:</strong> MP4</div>", unsafe_allow_html=True)

                    # Clear the download container as we've integrated it
                    download_container.empty()
                else:
                    status_container.error("Could not download the video. Make sure the URL contains a video and is publicly accessible.")

            except Exception as e:
                status_container.error(f"An error occurred: {str(e)}")

    # History section
    with st.expander("Download History", expanded=False):
        if len(st.session_state.ig_download_history) == 0:
            # Create a custom info message that works in both light and dark modes
            st.markdown("""
            <div style="
                background-color: #E1F5FE; 
                border-left: 5px solid #039BE5; 
                color: #01579B;
                padding: 20px; 
                border-radius: 10px; 
                margin-bottom: 20px;
                font-weight: bold;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                You haven't downloaded any videos yet.
            </div>
            """, unsafe_allow_html=True)
        else:
            # Display download history
            for i, item in enumerate(reversed(st.session_state.ig_download_history)):
                st.markdown(f"**URL:** {item['url']}")
                st.markdown(f"**Downloaded:** {item['timestamp']}")

                # Add download button if file still exists
                if os.path.exists(item["file_path"]):
                    with open(item["file_path"], "rb") as file:
                        st.download_button(
                            label="Download Again",
                            data=file.read(),
                            file_name=os.path.basename(item["file_path"]),
                            mime="video/mp4",
                            key=f"ig_history_download_{i}"
                        )
                else:
                    st.error("File no longer available")

                st.markdown("---")

# Footer
st.markdown("---")
st.caption("Video Downloader - Use responsibly and respect copyright")
st.caption("This application supports YouTube and Instagram video downloads")
