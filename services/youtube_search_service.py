"""
YouTube Search Service
Search YouTube videos using yt-dlp (no API key required)
Uses oEmbed API to get official embed code
Supports video download for local playback
"""

import os
import sys
import subprocess
import json
import threading
import time
import urllib.request
import urllib.parse
from typing import List, Dict, Optional, Callable, Tuple

class YouTubeSearchService:
    """Search YouTube for videos using yt-dlp"""
    
    # Cache directory for downloaded videos
    VIDEO_CACHE_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "video_cache"
    )
    
    # Max age for cached videos (24 hours)
    CACHE_MAX_AGE = 24 * 60 * 60
    
    def __init__(self):
        self._cache: Dict[str, List[dict]] = {}
        self._ensure_cache_dir()
    
    def search(self, query: str, max_results: int = 5) -> List[dict]:
        """
        Search YouTube for videos matching query
        
        Returns list of dicts with:
        - id: Video ID
        - url: Full YouTube URL
        - title: Video title
        - channel: Channel name
        - duration: Duration string
        - thumbnail: Thumbnail URL
        """
        # Check cache
        cache_key = f"{query}:{max_results}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            import sys
            
            # Use yt-dlp as Python module
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--flat-playlist",
                "--dump-json",
                "--no-warnings",
                "--quiet",
                f"ytsearch{max_results}:{query}"
            ]
            
            print(f"[YouTubeSearch] Searching: {query}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                print(f"[YouTubeSearch] yt-dlp error: {result.stderr}")
                return []
            
            videos = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    videos.append({
                        'id': data.get('id', ''),
                        'url': f"https://www.youtube.com/watch?v={data.get('id', '')}",
                        'title': data.get('title', ''),
                        'channel': data.get('channel', data.get('uploader', '')),
                        'duration': self._format_duration(data.get('duration')),
                        'thumbnail': data.get('thumbnail', ''),
                    })
                except json.JSONDecodeError:
                    continue
            
            # Cache results
            self._cache[cache_key] = videos
            return videos
            
        except subprocess.TimeoutExpired:
            print("[YouTubeSearch] Search timed out")
            return []
        except FileNotFoundError:
            print("[YouTubeSearch] yt-dlp not found. Please install: pip install yt-dlp")
            return []
        except Exception as e:
            print(f"[YouTubeSearch] Error: {e}")
            return []
    
    def search_async(self, query: str, callback: Callable[[List[dict]], None], 
                     max_results: int = 5) -> None:
        """Search YouTube asynchronously"""
        def task():
            results = self.search(query, max_results)
            callback(results)
        
        thread = threading.Thread(target=task, daemon=True)
        thread.start()
    
    def get_best_match(self, quest_name: str, search_prefix: str = "Where Winds Meet",
                       search_suffix: str = "guide") -> Optional[dict]:
        """
        Get the best matching video for a quest name
        
        Args:
            quest_name: Name of the quest
            search_prefix: Prefix to add to search (default: "Where Winds Meet")
            search_suffix: Suffix to add to search (default: "guide")
        
        Returns:
            First matching video dict or None
        """
        query = f"{search_prefix} {quest_name} {search_suffix}".strip()
        results = self.search(query, max_results=1)
        return results[0] if results else None
    
    def get_embed_url(self, video_id: str, autoplay: bool = True) -> str:
        """Get embeddable YouTube URL"""
        url = f"https://www.youtube.com/embed/{video_id}"
        if autoplay:
            url += "?autoplay=1"
        return url
    
    def _format_duration(self, seconds) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if not seconds:
            return ""
        
        # Convert to int (yt-dlp may return float)
        seconds = int(seconds)
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    
    def clear_cache(self) -> None:
        """Clear search cache"""
        self._cache.clear()
    
    def get_oembed(self, video_url: str, maxwidth: int = 480, maxheight: int = 360) -> Optional[dict]:
        """
        Get oEmbed data from YouTube
        
        Args:
            video_url: YouTube video URL
            maxwidth: Maximum embed width
            maxheight: Maximum embed height
        
        Returns:
            oEmbed data dict with 'html' embed code, or None if failed
        """
        try:
            # YouTube oEmbed endpoint
            oembed_url = "https://www.youtube.com/oembed"
            params = {
                "url": video_url,
                "format": "json",
                "maxwidth": maxwidth,
                "maxheight": maxheight
            }
            
            full_url = f"{oembed_url}?{urllib.parse.urlencode(params)}"
            
            request = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                print(f"[YouTubeSearch] oEmbed response: title={data.get('title')}")
                return data
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"[YouTubeSearch] Video embedding disabled for: {video_url}")
            else:
                print(f"[YouTubeSearch] oEmbed HTTP error {e.code}: {e}")
            return None
        except Exception as e:
            print(f"[YouTubeSearch] oEmbed error: {e}")
            return None
    
    def get_embed_html(self, video_url: str, width: int = 480, height: int = 360, 
                       autoplay: bool = True) -> Tuple[Optional[str], bool]:
        """
        Get embed HTML for a video, checking if embedding is allowed
        
        Args:
            video_url: YouTube video URL
            width: Embed width
            height: Embed height
            autoplay: Whether to add autoplay
        
        Returns:
            (embed_html, is_embeddable) - HTML code and whether video can be embedded
        """
        oembed = self.get_oembed(video_url, width, height)
        
        if oembed and 'html' in oembed:
            embed_html = oembed['html']
            
            # Add autoplay if requested
            if autoplay and 'autoplay' not in embed_html:
                embed_html = embed_html.replace(
                    'src="', 
                    'src="'
                ).replace(
                    '?feature=oembed',
                    '?feature=oembed&autoplay=1'
                )
            
            return embed_html, True
        
        return None, False
    
    def _ensure_cache_dir(self) -> None:
        """Ensure video cache directory exists"""
        if not os.path.exists(self.VIDEO_CACHE_DIR):
            os.makedirs(self.VIDEO_CACHE_DIR, exist_ok=True)
    
    def _get_video_id(self, video_url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        url = video_url
        
        if "youtube.com/embed/" in url or "youtube-nocookie.com/embed/" in url:
            return url.split("embed/")[1].split("?")[0]
        elif "youtube.com/watch?v=" in url:
            return url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com/v/" in url:
            return url.split("/v/")[1].split("?")[0]
        
        return None
    
    def get_cached_video(self, video_url: str) -> Optional[str]:
        """
        Check if video is already cached
        
        Returns:
            Path to cached MP4 file, or None if not cached
        """
        video_id = self._get_video_id(video_url)
        if not video_id:
            return None
        
        cache_path = os.path.join(self.VIDEO_CACHE_DIR, f"{video_id}.mp4")
        
        if os.path.exists(cache_path):
            # Check if cache is still fresh
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age < self.CACHE_MAX_AGE:
                print(f"[YouTubeSearch] Using cached video: {cache_path}")
                return cache_path
            else:
                # Remove stale cache
                try:
                    os.remove(cache_path)
                except:
                    pass
        
        return None
    
    def download_video(self, video_url: str, 
                       progress_callback: Optional[Callable[[str, int], None]] = None) -> Optional[str]:
        """
        Download video using yt-dlp
        
        Args:
            video_url: YouTube video URL
            progress_callback: Callback(status, percent) for progress updates
        
        Returns:
            Path to downloaded MP4 file, or None if failed
        """
        video_id = self._get_video_id(video_url)
        if not video_id:
            print(f"[YouTubeSearch] Could not extract video ID from: {video_url}")
            return None
        
        # Check cache first
        cached = self.get_cached_video(video_url)
        if cached:
            if progress_callback:
                progress_callback("Đã có sẵn!", 100)
            return cached
        
        output_path = os.path.join(self.VIDEO_CACHE_DIR, f"{video_id}.mp4")
        
        try:
            if progress_callback:
                progress_callback("Đang tải video...", 10)
            
            # Use yt-dlp to download video
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", "best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best",
                "-o", output_path,
                "--no-warnings",
                "--no-playlist",
                video_url
            ]
            
            print(f"[YouTubeSearch] Downloading video: {video_id}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                print(f"[YouTubeSearch] Download failed: {result.stderr}")
                if progress_callback:
                    progress_callback("Lỗi tải video", 0)
                return None
            
            if os.path.exists(output_path):
                print(f"[YouTubeSearch] Downloaded: {output_path}")
                if progress_callback:
                    progress_callback("Hoàn tất!", 100)
                return output_path
            
            # Check for format variations in filename
            for f in os.listdir(self.VIDEO_CACHE_DIR):
                if f.startswith(video_id):
                    actual_path = os.path.join(self.VIDEO_CACHE_DIR, f)
                    print(f"[YouTubeSearch] Downloaded (alt name): {actual_path}")
                    if progress_callback:
                        progress_callback("Hoàn tất!", 100)
                    return actual_path
            
            return None
            
        except subprocess.TimeoutExpired:
            print("[YouTubeSearch] Download timed out")
            if progress_callback:
                progress_callback("Quá thời gian", 0)
            return None
        except Exception as e:
            print(f"[YouTubeSearch] Download error: {e}")
            if progress_callback:
                progress_callback(f"Lỗi: {str(e)[:30]}", 0)
            return None
    
    def download_video_async(self, video_url: str,
                             progress_callback: Optional[Callable[[str, int], None]] = None,
                             on_complete: Optional[Callable[[Optional[str]], None]] = None) -> None:
        """Download video asynchronously"""
        def task():
            result = self.download_video(video_url, progress_callback)
            if on_complete:
                on_complete(result)
        
        thread = threading.Thread(target=task, daemon=True)
        thread.start()
    
    def cleanup_cache(self) -> int:
        """
        Remove old cached videos
        
        Returns:
            Number of files removed
        """
        removed = 0
        
        if not os.path.exists(self.VIDEO_CACHE_DIR):
            return 0
        
        current_time = time.time()
        
        for filename in os.listdir(self.VIDEO_CACHE_DIR):
            filepath = os.path.join(self.VIDEO_CACHE_DIR, filename)
            try:
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > self.CACHE_MAX_AGE:
                        os.remove(filepath)
                        removed += 1
                        print(f"[YouTubeSearch] Removed old cache: {filename}")
            except Exception as e:
                print(f"[YouTubeSearch] Cleanup error for {filename}: {e}")
        
        return removed
