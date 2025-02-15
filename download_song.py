import yt_dlp
import sys
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

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python download_song.py <youtube_url> [user_id]", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    result = download_song(url, user_id)
    
    if result['success']:
        print(f"Downloaded: {result['file_path']}")
        sys.exit(0)
    else:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
