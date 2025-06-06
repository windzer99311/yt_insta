import re
import os
import time
import json
import tempfile
import requests
import instaloader
from datetime import datetime
from bs4 import BeautifulSoup
from instaloader.exceptions import InvalidArgumentException, TwoFactorAuthRequiredException, ConnectionException, BadCredentialsException

def is_valid_instagram_url(url):
    """
    Check if the URL is a valid Instagram URL
    """
    instagram_pattern = r"(https?:\/\/)?(www\.)?instagram\.com\/(?:p|reel|tv)\/([a-zA-Z0-9_-]+)\/?.*"
    return bool(re.match(instagram_pattern, url))

def get_shortcode_from_url(url):
    """
    Extract the shortcode from an Instagram URL
    """
    instagram_pattern = r"(https?:\/\/)?(www\.)?instagram\.com\/(?:p|reel|tv)\/([a-zA-Z0-9_-]+)\/?.*"
    match = re.match(instagram_pattern, url)
    if match:
        return match.group(3)
    return None

def get_instagram_post_info(shortcode):
    """
    Get information about an Instagram post using its shortcode
    """
    try:
        # Initialize Instaloader
        L = instaloader.Instaloader(download_pictures=False,
                                   download_videos=False,
                                   download_video_thumbnails=False,
                                   download_geotags=False,
                                   download_comments=False,
                                   save_metadata=False)

        # Get post from shortcode
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Extract post information
        post_info = {
            "username": post.owner_username,
            "full_name": post.owner_profile.full_name if hasattr(post.owner_profile, 'full_name') else "",
            "caption": post.caption if post.caption else "",
            "date": post.date.strftime("%Y-%m-%d %H:%M:%S"),
            "likes": post.likes,
            "comments": post.comments,
            "is_video": post.is_video,
            "location": post.location.name if post.location else None,
            "hashtags": list(post.caption_hashtags) if post.caption else [],
            "mentions": list(post.caption_mentions) if post.caption else [],
            "profile_pic_url": post.owner_profile.profile_pic_url
        }

        return post_info
    except Exception as e:
        # Return basic info if detailed info can't be retrieved
        return {
            "username": "unknown",
            "full_name": "",
            "caption": "",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "likes": 0,
            "comments": 0,
            "is_video": True,
            "location": None,
            "hashtags": [],
            "mentions": [],
            "profile_pic_url": ""
        }

def get_video_duration(video_path):
    """
    Get the duration of a video file in seconds (estimate)
    """
    try:
        # Using file size as a very rough estimate
        # A more accurate approach would require a library like ffmpeg
        file_size = os.path.getsize(video_path)
        # Rough estimate: 1MB per 10 seconds of video at moderate quality
        estimated_duration = file_size / (1024 * 1024 * 0.1)  
        return round(estimated_duration, 1)
    except:
        return 0

def get_popular_instagram_tags():
    """
    Get a list of popular Instagram hashtags
    """
    # These are manually curated popular hashtags
    # In a real app, this could be dynamically updated
    return [
        "love", "instagood", "photooftheday", "fashion", "beautiful", 
        "happy", "cute", "tbt", "like4like", "followme", "picoftheday", 
        "follow", "me", "selfie", "summer", "art", "instadaily", "friends", 
        "repost", "nature", "girl", "fun", "style", "smile", "food"
    ]

def get_video_quality(video_path):
    """
    Estimate video quality based on file size (HD, SD, etc.)
    """
    try:
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if file_size_mb > 50:
            return "HD+ (High Definition)"
        elif file_size_mb > 20:
            return "HD (High Definition)"
        elif file_size_mb > 10:
            return "SD (Standard Definition)"
        else:
            return "LD (Low Definition)"
    except:
        return "Unknown"

def download_instagram_video(url, quality="highest"):
    """
    Download video from Instagram URL and return the path to the downloaded file

    Parameters:
    - url: Instagram video URL
    - quality: Video quality (highest, medium, low) - currently only highest is implemented

    Returns:
    - Path to downloaded video file
    """
    shortcode = get_shortcode_from_url(url)
    if not shortcode:
        raise ValueError("Could not extract shortcode from URL")

    # Create a temporary file to store the video
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{shortcode}.mp4")

    # Initialize Instaloader with options
    L = instaloader.Instaloader(
        dirname_pattern=temp_dir,
        filename_pattern=shortcode,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )

    try:
        # Download the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Check if post has video
        if not post.is_video:
            return None

        # Download only the video
        L.download_post(post, target=shortcode)

        # Find the downloaded video file
        for file in os.listdir(temp_dir):
            if file.endswith('.mp4') and shortcode in file:
                video_path = os.path.join(temp_dir, file)

                # If a different quality was requested, we would convert here
                # Currently this is not implemented and the original quality is returned

                return video_path

        return None

    except (InvalidArgumentException, ConnectionException) as e:
        raise Exception(f"Error accessing Instagram: {str(e)}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")

def batch_download_videos(urls):
    """
    Download multiple videos at once

    Parameters:
    - urls: List of Instagram URLs

    Returns:
    - Dictionary mapping URLs to their download paths or errors
    """
    results = {}

    for url in urls:
        try:
            if not is_valid_instagram_url(url):
                results[url] = {"success": False, "error": "Invalid Instagram URL"}
                continue

            video_path = download_instagram_video(url)
            if video_path:
                results[url] = {"success": True, "path": video_path}
            else:
                results[url] = {"success": False, "error": "Could not download the video"}

        except Exception as e:
            results[url] = {"success": False, "error": str(e)}

    return results

def extract_hashtags_from_caption(caption):
    """
    Extract hashtags from post caption
    """
    if not caption:
        return []

    hashtag_pattern = r"#(\w+)"
    hashtags = re.findall(hashtag_pattern, caption)
    return hashtags

def get_related_hashtags(hashtag):
    """
    Get a list of related hashtags (simplified version)
    """
    # This is a simple implementation 
    # In a real app, this would query Instagram or use a more sophisticated algorithm
    popular_tags = get_popular_instagram_tags()

    # Just return some random tags as "related"
    import random
    num_related = min(5, len(popular_tags))
    return random.sample(popular_tags, num_related)
