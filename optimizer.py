from pytubefix import YouTube
video_stream_list=[]
def video_metadata(link):
    yt = YouTube(link)

    # Collect basic info quickly
    video_title = yt.title
    video_length = yt.length
    video_thumbnail = yt.thumbnail_url

    # Format to HH:MM:SS
    hh, mm, ss = video_length // 3600, (video_length % 3600) // 60, (video_length % 60)
    video_duration = f"{hh:02}:{mm:02}:{ss:02}"

    # Prepare containers
    quality_selected = {}

    # Filter only video streams (non-progressive = video only)
    streams = yt.streams.filter(progressive=False, type='video')

    # Avoid repeated file_size calls (slow), parse and store once
    for stream in streams:
        if not stream.resolution:
            continue

        # Extract mime type (e.g., 'video/mp4' -> 'mp4')
        ext = stream.mime_type.split('/')[-1]

        # Get file_size (can be slow, so cache it smartly)

        size_mb = round(stream.filesize / (1024 * 1024), 2)


        # Build label (e.g., "1080p 60fps 29.25mb mp4")
        label = f"{stream.resolution} {stream.fps}fps {size_mb}mb {ext}"

        # Store info
        video_stream_list.append(label)
        quality_selected[label] = stream.itag

    # Sort qualities by resolution (e.g., 360p, 720p, 1080p)
    quality_option = sorted(
        video_stream_list,
        key=lambda x: int(x.split()[0].replace('p', ''))
    )


    return {
        'video_title': video_title,
        'video_duration': video_duration,
        'video_thumbnail': video_thumbnail,
        'quality_option': quality_option,
        'quality_selected': quality_selected
    }
def file_stream_data(link, quality_selected):
    yt = YouTube(link)
    video_selected=yt.streams.get_by_itag(quality_selected)
    audio_selected=yt.streams.filter(only_audio=True).asc().first()
    video_size,audio_size=video_selected.filesize,audio_selected.filesize
    video_streaming_url,audio_streaming_url=video_selected.url,audio_selected.url

    return {
            'video_size': video_size,
            'audio_size': audio_size,
            'video_streaming_url':video_streaming_url,
            'audio_streaming_url':audio_streaming_url
            }
