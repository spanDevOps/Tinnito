import yt_dlp
import os

def download_song(url, user_id=None):
    """Download a song from YouTube URL"""
    # Create user-specific directory
    output_dir = os.path.join('mpthrees', user_id) if user_id else 'mpthrees'
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            song_path = os.path.join(output_dir, f"{info['title']}.mp3")
            return {
                'success': True,
                'file_path': song_path,
                'title': info['title'],
                'user_id': user_id
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
