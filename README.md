# AI Meeting Assistant Backend

A Flask-based REST API backend for the AI Meeting Assistant application with CORS support, health monitoring, and deployment-ready configuration.

## 🚀 Features

- **CORS Enabled**: Full CORS support for React frontend
- **Health Monitoring**: Simple `/api/health` endpoint
- **File Upload**: Audio file processing with Supabase storage
- **AI Processing**: Transcription (RapidAPI) + AI analysis (Gemini 2.0 Flash)
- **Database**: PostgreSQL with Neon
- **Deployment Ready**: Configured for Render deployment

## 🛠️ Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start the Server**
   ```bash
   python start.py
   # or
   python app.py
   ```

4. **Test Health Endpoint**
   ```bash
   curl http://localhost:5000/api/health
   # Response: {"status": "ok"}
   ```

### Environment Variables

```env
# Database
NEON_DATABASE_URL=your_neon_database_url

# Storage
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# AI Services
RAPIDAPI_KEY=your_rapidapi_key
GEMINI_API_KEY=your_gemini_api_key

# Flask
SECRET_KEY=your_secret_key
FLASK_ENV=development  # or production
PORT=5000
```

## 📡 API Endpoints

### Health Check
- `GET /api/health` - Simple health check
- `GET /api/health/detailed` - Detailed service status

### Authentication
- `POST /api/auth/verify` - Verify Firebase user

### Meetings
- `GET /api/meetings` - List meetings
- `GET /api/meetings/{id}` - Get meeting details
- `GET /api/meetings/{id}/timeline` - Get meeting timeline
- `DELETE /api/meetings/{id}` - Delete meeting

### Tasks
- `GET /api/tasks` - List tasks
- `PUT /api/tasks/{id}/status` - Update task status

### Upload
- `POST /api/upload/audio` - Upload audio file
- `GET /api/upload/status/{meeting_id}` - Get processing status

## 🌐 CORS Configuration

The backend is configured to allow all origins for `/api/*` routes:

```python
CORS(app, 
     resources={
         r"/api/*": {
             "origins": "*",  # Allow all origins
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
             "supports_credentials": False
         }
     })
```

## 🚀 Deployment (Render)

1. **Push to GitHub**
2. **Connect to Render**
3. **Use render.yaml configuration**
4. **Set environment variables in Render dashboard**

### Render Configuration

The `render.yaml` file is included for easy deployment:

```yaml
services:
  - type: web
    name: ai-meeting-assistant-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    healthCheckPath: /api/health
```

## 🔧 Development

### Project Structure
```
backend/
├── app.py              # Main Flask application
├── start.py            # Development startup script
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
├── config/
│   ├── database.py     # Database configuration
│   └── storage.py      # Storage configuration
├── routes/
│   ├── auth.py         # Authentication routes
│   ├── meetings.py     # Meeting routes
│   ├── tasks.py        # Task routes
│   ├── upload.py       # Upload routes
│   └── health.py       # Health check routes
└── services/
    ├── transcription.py    # Audio transcription
    ├── ai_processor.py     # AI processing
    └── calendar_sync.py    # Calendar integration
```

### Testing CORS

```bash
# Test simple health endpoint
curl -X GET http://localhost:5000/api/health

# Test CORS preflight
curl -X OPTIONS http://localhost:5000/api/health \
  -H "Origin: http://localhost:8080" \
  -H "Access-Control-Request-Method: GET"

# Test cross-origin request
curl -X GET http://localhost:5000/api/health \
  -H "Origin: http://localhost:8080"
```

## 📊 Health Monitoring

- **Simple Health**: `GET /api/health` returns `{"status": "ok"}`
- **Detailed Health**: `GET /api/health/detailed` returns full service status
- **Individual Services**: 
  - `/api/health/detailed/database`
  - `/api/health/detailed/storage`
  - `/api/health/detailed/transcription`
  - `/api/health/detailed/ai`

## 🔒 Security

- CORS configured for frontend origins
- File upload size limits (100MB)
- Environment-based configuration
- Production-ready error handling

## 🐛 Troubleshooting

### Common Issues

1. **CORS Errors**: Check that frontend URL is in CORS origins
2. **Database Connection**: Verify NEON_DATABASE_URL
3. **API Keys**: Ensure all required environment variables are set
4. **Port Conflicts**: Change PORT environment variable

### Logs

```bash
# View application logs
python app.py

# Check health status
curl http://localhost:5000/api/health
```

## 📝 License

MIT License - see LICENSE file for details.