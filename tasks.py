import yt_dlp
import os
from rq import get_current_job
import boto3
from botocore.client import Config
from datetime import datetime, timedelta

def update_progress(progress, message=''):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.meta['message'] = message
        job.save_meta()

def get_r2_client():
    """Get Cloudflare R2 client"""
    return boto3.client('s3',
        endpoint_url=os.environ['R2_ENDPOINT_URL'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4')
    )

def cleanup_old_files():
    """Delete files older than 15 minutes"""
    r2 = get_r2_client()
    cutoff_time = datetime.utcnow() - timedelta(minutes=15)
    
    try:
        objects = r2.list_objects_v2(Bucket=os.environ['R2_BUCKET'])
        for obj in objects.get('Contents', []):
            if obj['LastModified'].replace(tzinfo=None) < cutoff_time:
                r2.delete_object(
                    Bucket=os.environ['R2_BUCKET'],
                    Key=obj['Key']
                )
    except Exception as e:
        print(f"Error cleaning up old files: {e}")

def process_youtube_url(url, user_id):
    """Download YouTube video as MP3 and upload to R2"""
    update_progress(0.1, 'Starting download...')
    
    try:
        # Create temp directory for downloads
        temp_dir = f"temp_{user_id}"
        os.makedirs(temp_dir, exist_ok=True)

        # Download options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: update_progress(
                min(0.6, 0.1 + (d.get('downloaded_bytes', 0) / d.get('total_bytes', 1)) * 0.5)
                if d['status'] == 'downloading' else None,
                f"Downloading... {d.get('_percent_str', '')}"
            )]
        }

        update_progress(0.2, 'Extracting audio...')
        
        # Download and convert to MP3
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info['title']
            mp3_file = f"{temp_dir}/{title}.mp3"
            
            update_progress(0.7, 'Uploading to storage...')
            
            # Get R2 client and clean up old files
            r2 = get_r2_client()
            cleanup_old_files()
            
            # Delete any existing files for this user
            try:
                r2.delete_object(
                    Bucket=os.environ['R2_BUCKET'],
                    Key=f"{user_id}/current.mp3"
                )
            except:
                pass  # Ignore if no file exists
            
            # Upload with 15-minute expiry
            r2.upload_file(
                mp3_file,
                os.environ['R2_BUCKET'],
                f"{user_id}/{title}.mp3",
                ExtraArgs={
                    'Metadata': {
                        'expiry': (datetime.now() + timedelta(minutes=15)).isoformat()
                    }
                }
            )
            
            # Generate presigned URL valid for 15 minutes
            presigned_url = r2.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': os.environ['R2_BUCKET'],
                    'Key': f"{user_id}/{title}.mp3"
                },
                ExpiresIn=900  # 15 minutes
            )
            
            # Clean up local file
            os.remove(mp3_file)
            os.rmdir(temp_dir)
            
            update_progress(1.0, 'Complete!')
            
            return {
                'status': 'complete',
                'title': title,
                'download_url': presigned_url
            }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
