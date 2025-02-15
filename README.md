# Song Downloader

A web application that downloads songs from YouTube URLs and provides direct download links.

## Features
- Simple web interface for submitting YouTube URLs
- Direct MP3 downloads to your device
- Keeps track of last 5 downloaded songs
- Automatic cleanup of old files
- Works from any device with a web browser

## Local Development

### Using Docker
1. Install Docker and Docker Compose
2. Build and run:
```bash
docker-compose up --build
```
3. Access at http://localhost:5000

### Without Docker
1. Install Python 3.12
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run the server:
```bash
python url_server.py
```

## Deployment to Vercel

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy:
```bash
vercel
```

4. For production deployment:
```bash
vercel --prod
```

## Important Notes

### Storage on Vercel
Since Vercel uses serverless functions, file storage is ephemeral. For production use, you should:
1. Use a cloud storage service (like AWS S3) for storing MP3 files
2. Use a database service for tracking downloads

### Environment Variables
Set these in your Vercel dashboard:
- `FLASK_ENV`: Set to 'production' for production deployment
- Add any other required API keys or configuration

## Architecture
- Flask web application
- File-based storage for development
- Containerized for easy deployment
- Vercel-ready configuration

## Limitations
- Vercel has a maximum execution time of 10 seconds for hobby accounts
- File storage is temporary in serverless environments
- Consider using cloud storage for production use
