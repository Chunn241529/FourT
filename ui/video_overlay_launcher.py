"""
Video Overlay Launcher Script
Spawned as subprocess to show embedded YouTube player or local video
"""

import sys
import os
import webbrowser
import webview


class Api:
    """JavaScript API for window control"""
    
    def __init__(self, window, video_url):
        self._window = window
        self._video_url = video_url
    
    def close_window(self):
        """Close the window"""
        self._window.destroy()
    
    def open_in_browser(self):
        """Open video in default browser"""
        if not self._video_url.startswith('file://') and not os.path.exists(self._video_url):
            webbrowser.open(self._video_url)
        self._window.destroy()


def main():
    if len(sys.argv) < 4:
        print("Usage: video_overlay_launcher.py <video_url> <title> <width> <height> <autoplay> [embed_html] [is_local]")
        sys.exit(1)
    
    video_url = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "Video Guide"
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 480
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 360
    autoplay = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
    embed_html = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None
    is_local = sys.argv[7].lower() == 'true' if len(sys.argv) > 7 else False
    
    print(f"[VideoOverlay] is_local={is_local}, video_url={video_url}")
    
    # For local files, load file directly
    if is_local and os.path.exists(video_url):
        print(f"[VideoOverlay] Loading local file: {video_url}")
        # Create window pointing directly to local file
        window = webview.create_window(
            title="",
            url=video_url,  # Load file directly!
            width=width,
            height=height,
            resizable=True,
            frameless=False,  # Use native frame for local video
            on_top=True,
        )
        webview.start()
        return
    
    # Get watch URL for browser fallback
    if is_local:
        watch_url = video_url
    else:
        video_id = get_video_id(video_url)
        watch_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else video_url
    
    # Generate full HTML
    html = get_html(watch_url, title, embed_html, is_local, video_url)
    
    # Create window with API
    window = webview.create_window(
        title="",
        html=html,
        width=width,
        height=height + 36,
        resizable=True,
        frameless=True,
        on_top=True,
        easy_drag=True,
    )
    
    # Expose API to JavaScript
    api = Api(window, watch_url)
    window.expose(api.close_window)
    window.expose(api.open_in_browser)
    
    webview.start()


def get_video_id(video_url: str) -> str:
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


def get_html(watch_url: str, title: str, embed_html: str = None, 
             is_local: bool = False, local_path: str = None) -> str:
    """Generate HTML for the video player"""
    
    if is_local and local_path:
        # Local video player using HTML5 video tag
        # Use proper file path format for Windows
        file_path = local_path.replace('\\', '/')
        if not file_path.startswith('/'):
            file_path = '/' + file_path
        file_url = f"file://{file_path}"
        
        print(f"[VideoOverlay] Local file URL: {file_url}")
        
        video_content = f'''<video 
            id="localVideo"
            style="position:absolute;top:0;left:0;width:100%;height:100%;background:#000;"
            controls autoplay>
            <source src="{file_url}" type="video/mp4">
            Your browser does not support video playback.
        </video>
        <script>
            // Handle video load error
            document.getElementById('localVideo').onerror = function() {{
                console.error('Video load error');
            }};
        </script>'''
    elif embed_html:
        # Use oEmbed HTML if available
        video_content = embed_html.replace(
            '<iframe', 
            '<iframe style="position:absolute;top:0;left:0;width:100%;height:100%;border:none;"'
        )
    else:
        # Fallback - create generic iframe
        video_id = get_video_id(watch_url)
        if video_id:
            video_content = f'''<iframe 
                style="position:absolute;top:0;left:0;width:100%;height:100%;border:none;"
                src="https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1&playsinline=1&rel=0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>'''
        else:
            video_content = f'<a href="{watch_url}" style="color:#00d4ff;">Open Video</a>'
    
    # Determine if we should show browser button (hide for local videos)
    browser_btn = '' if is_local else '''<button class="btn btn-browser" onclick="pywebview.api.open_in_browser()" title="Mở trong Browser">🌐</button>'''
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                background: #1a1a2e;
                overflow: hidden;
                font-family: 'Segoe UI', sans-serif;
            }}
            .container {{
                width: 100vw;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }}
            .title-bar {{
                height: 36px;
                min-height: 36px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 12px;
                cursor: move;
                -webkit-app-region: drag;
                border-bottom: 1px solid #2a2a4a;
            }}
            .title {{
                color: #00d4ff;
                font-size: 12px;
                font-weight: 500;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                max-width: calc(100% - 100px);
            }}
            .btn-group {{
                display: flex;
                gap: 5px;
                -webkit-app-region: no-drag;
            }}
            .btn {{
                background: transparent;
                border: none;
                font-size: 14px;
                cursor: pointer;
                padding: 5px 8px;
                transition: all 0.2s;
                border-radius: 4px;
            }}
            .btn-browser {{
                color: #00d4ff;
            }}
            .btn-browser:hover {{
                background: rgba(0, 212, 255, 0.2);
            }}
            .btn-close {{
                color: #ff6b6b;
            }}
            .btn-close:hover {{
                background: rgba(255, 107, 107, 0.2);
            }}
            .video-container {{
                flex: 1;
                position: relative;
                background: #000;
            }}
            video {{
                background: #000;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="title-bar">
                <span class="title">{title}</span>
                <div class="btn-group">
                    {browser_btn}
                    <button class="btn btn-close" onclick="pywebview.api.close_window()" title="Đóng">✕</button>
                </div>
            </div>
            <div class="video-container">
                {video_content}
            </div>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    main()
