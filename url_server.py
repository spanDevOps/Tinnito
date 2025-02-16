from flask import Flask, render_template, request, jsonify, session
import redis
from rq import Queue
from tasks import process_youtube_url
import os
import json
import boto3
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('tinnito')
logger.setLevel(logging.INFO)

# Add file handler with rotation
os.makedirs('logs', exist_ok=True)
file_handler = RotatingFileHandler('logs/tinnito.log', maxBytes=1024*1024, backupCount=5)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s - {"component": "%(name)s", "path": "%(pathname)s:%(lineno)d"}'
))
logger.addHandler(file_handler)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-this')

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
redis_conn = redis.from_url(redis_url)
q = Queue(connection=redis_conn)

@app.route('/')
def index():
    return '''
    <html>
        <head>
            <title>YouTube Song Downloader</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                }
                .form { 
                    margin: 20px 0;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                @media (min-width: 768px) {
                    .form {
                        flex-direction: row;
                    }
                }
                input[type=text] { 
                    width: 100%; 
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 16px;
                }
                input[type=submit], .download-btn { 
                    padding: 12px 24px;
                    background: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    text-align: center;
                    text-decoration: none;
                    min-width: 120px;
                }
                .status { 
                    margin: 20px 0; 
                    padding: 15px;
                    border-radius: 4px;
                    display: none;
                }
                .error { 
                    background: #ffebee; 
                    color: #c62828;
                }
                .success { 
                    background: #e8f5e9; 
                    color: #2e7d32;
                }
                .progress {
                    width: 100%;
                    height: 4px;
                    background: #f5f5f5;
                    border-radius: 4px;
                    overflow: hidden;
                    margin-top: 10px;
                }
                .progress-bar {
                    width: 0%;
                    height: 100%;
                    background: #4CAF50;
                    transition: width 0.3s ease;
                }
            </style>
            <script>
                function submitForm(event) {
                    event.preventDefault();
                    const url = document.getElementById('url').value;
                    const status = document.getElementById('status');
                    const progress = document.createElement('div');
                    progress.className = 'progress';
                    progress.innerHTML = '<div class="progress-bar"></div>';
                    
                    status.style.display = 'block';
                    status.className = 'status';
                    status.textContent = 'Processing...';
                    status.appendChild(progress);
                    
                    fetch('/download', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'url=' + encodeURIComponent(url)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            status.className = 'status error';
                            status.textContent = 'Error: ' + data.error;
                        } else {
                            status.className = 'status success';
                            status.textContent = 'Processing started...';
                            checkStatus(data.job_id);
                        }
                    })
                    .catch(error => {
                        status.className = 'status error';
                        status.textContent = 'Error: ' + error;
                    });
                }
                
                function checkStatus(jobId) {
                    const status = document.getElementById('status');
                    const progressBar = status.querySelector('.progress-bar');
                    
                    fetch('/status/' + jobId)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            status.className = 'status error';
                            status.textContent = 'Error: ' + data.error;
                        } else if (data.status === 'finished' && data.result && data.result.success) {
                            status.className = 'status success';
                            const downloadLink = document.createElement('div');
                            downloadLink.innerHTML = `
                                <p>Download ready!</p>
                                <a href="${data.result.download_url}" class="download-btn" target="_blank">
                                    Download "${data.result.title}"
                                </a>
                            `;
                            status.innerHTML = '';
                            status.appendChild(downloadLink);
                        } else if (data.status === 'failed') {
                            status.className = 'status error';
                            status.textContent = 'Download failed: ' + data.error;
                        } else {
                            if (progressBar) {
                                progressBar.style.width = Math.min((data.progress || 0) * 100, 90) + '%';
                            }
                            status.textContent = 'Processing... ' + (data.message || '');
                            setTimeout(() => checkStatus(jobId), 1000);
                        }
                    });
                }
            </script>
        </head>
        <body>
            <h1>YouTube Song Downloader</h1>
            <div class="form">
                <input type="text" id="url" placeholder="Enter YouTube URL" required>
                <input type="submit" value="Download" onclick="submitForm(event)">
            </div>
            <div id="status" class="status"></div>
        </body>
    </html>
    '''

@app.route('/download', methods=['POST'])
def download_url():
    url = request.form.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Get user session ID or create new one
    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()
    
    # Queue the download job
    try:
        job = q.enqueue(
            'tasks.process_youtube_url',
            args=(url, session['user_id']),
            job_timeout='10m'
        )
        return jsonify({
            "message": "Download started",
            "job_id": job.id
        })
    except Exception as e:
        return jsonify({"error": f"Failed to queue download: {str(e)}"}), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    job = q.fetch_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    status = {
        "id": job.id,
        "status": job.get_status(),
        "result": job.result,
        "error": str(job.exc_info) if job.exc_info else None,
        "progress": getattr(job, 'meta', {}).get('progress', 0),
        "message": getattr(job, 'meta', {}).get('message', '')
    }
    return jsonify(status)

@app.route('/health')
def health_check():
    """Health check endpoint that verifies Redis and R2 connectivity."""
    request_id = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    logger.info(f'Health check initiated - RequestID: {request_id}')
    
    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': 'unknown',
        'request_id': request_id,
        'checks': {
            'redis': {
                'status': 'unhealthy'
            },
            'r2_storage': {
                'status': 'unhealthy'
            }
        }
    }

    # Check Redis
    try:
        logger.info(f'Testing Redis connection - RequestID: {request_id}')
        redis_conn.ping()
        status['checks']['redis'] = {
            'status': 'healthy',
            'message': 'Connected successfully'
        }
        logger.info(f'Redis check passed - RequestID: {request_id}')
    except Exception as e:
        error_msg = str(e)
        status['checks']['redis'] = {
            'status': 'unhealthy',
            'error': error_msg
        }
        status['status'] = 'unhealthy'
        logger.error(f'Redis check failed - RequestID: {request_id}, Error: {error_msg}')

    # Check R2
    try:
        logger.info(f'Testing R2 storage connection - RequestID: {request_id}')
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('R2_ENDPOINT_URL'),
            aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY')
        )
        bucket = os.getenv('R2_BUCKET')
        s3_client.head_bucket(Bucket=bucket)
        status['checks']['r2_storage'] = {
            'status': 'healthy',
            'message': f'Connected successfully to bucket {bucket}'
        }
        logger.info(f'R2 storage check passed - RequestID: {request_id}, Bucket: {bucket}')
    except Exception as e:
        error_msg = str(e)
        status['checks']['r2_storage'] = {
            'status': 'unhealthy',
            'error': error_msg
        }
        status['status'] = 'unhealthy'
        logger.error(f'R2 storage check failed - RequestID: {request_id}, Error: {error_msg}')

    response_code = 200 if status['status'] == 'healthy' else 500
    logger.info(f'Health check completed - RequestID: {request_id}, Status: {status["status"]}, Code: {response_code}')
    return jsonify(status), response_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
