# AI Meeting Assistant Backend - Production Deployment Guide

## Overview
This guide covers deploying the AI Meeting Assistant backend to Render.com using Docker.

## Prerequisites
- Render.com account
- GitHub repository with your code
- All required API keys and database credentials

## Environment Variables Setup

### Required Environment Variables
Set these in your Render dashboard:

```bash
# Flask Configuration
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production

# Database
NEON_DATABASE_URL=postgresql://username:password@host:port/database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Google Calendar API
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-backend-domain.onrender.com/api/auth/google/callback

# AI Services
GEMINI_API_KEY=your-gemini-api-key
RAPIDAPI_KEY=your-rapidapi-key

# CORS (replace with your frontend domain)
CORS_ORIGINS=https://your-frontend-domain.com,https://your-app.vercel.app

# Production Settings
WEB_CONCURRENCY=2
GUNICORN_TIMEOUT=120
```

## Deployment Steps

### 1. Connect Repository
1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository containing your backend

### 2. Configure Service
- **Name**: `ai-meeting-assistant-backend`
- **Environment**: `Docker`
- **Dockerfile Path**: `./backend/Dockerfile`
- **Docker Context**: `./backend`
- **Plan**: `Starter` (or higher for production)

### 3. Set Environment Variables
Add all the environment variables listed above in the Render dashboard.

### 4. Deploy
Click "Create Web Service" to start deployment.

## Google Calendar API Setup

### 1. Google Cloud Console Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials

### 2. OAuth Configuration
- **Application Type**: Web application
- **Authorized JavaScript Origins**: 
  - `https://your-frontend-domain.com`
  - `http://localhost:3000` (for development)
- **Authorized Redirect URIs**:
  - `https://your-backend-domain.onrender.com/api/auth/google/callback`
  - `http://localhost:5000/api/auth/google/callback` (for development)

### 3. Environment Variables
Set these in Render:
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-backend-domain.onrender.com/api/auth/google/callback
```

## Database Setup

### 1. Neon Database
1. Create account at [Neon](https://neon.tech/)
2. Create new database
3. Copy connection string
4. Set `NEON_DATABASE_URL` in Render

### 2. Supabase Storage
1. Create account at [Supabase](https://supabase.com/)
2. Create new project
3. Get URL and anon key
4. Set `SUPABASE_URL` and `SUPABASE_KEY` in Render

## Monitoring and Health Checks

### Health Check Endpoint
The service includes a health check at `/api/health` that:
- Returns 200 status
- Includes timestamp
- Validates basic functionality

### Logs
Monitor your application logs in the Render dashboard:
- Application logs
- Build logs
- Health check status

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify `NEON_DATABASE_URL` is correct
   - Check database is accessible from Render's IPs

2. **Google Calendar API Errors**
   - Verify OAuth credentials are correct
   - Check redirect URI matches exactly
   - Ensure Google Calendar API is enabled

3. **CORS Issues**
   - Update `CORS_ORIGINS` with your frontend domain
   - Ensure no trailing slashes in URLs

4. **Build Failures**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt
   - Check for missing files

### Debug Commands
```bash
# Check if service is running
curl https://your-backend-domain.onrender.com/api/health

# Test Google Calendar integration
curl -X GET "https://your-backend-domain.onrender.com/api/google-calendar/test"
```

## Production Optimizations

### Performance
- Uses Gunicorn with multiple workers
- Implements request timeouts
- Includes connection pooling
- Optimized Docker layers

### Security
- Non-root user in container
- Environment variable validation
- CORS properly configured
- Rate limiting enabled

### Monitoring
- Health checks every 30 seconds
- Structured logging
- Error tracking
- Performance metrics

## Scaling

### Horizontal Scaling
- Increase `WEB_CONCURRENCY` for more workers
- Use Render's auto-scaling features
- Consider database connection limits

### Vertical Scaling
- Upgrade to higher Render plan
- Increase memory and CPU allocation
- Optimize database queries

## Maintenance

### Regular Tasks
- Monitor logs for errors
- Update dependencies regularly
- Check API key expiration
- Monitor database performance

### Updates
- Deploy updates through Render dashboard
- Test in staging environment first
- Use blue-green deployment for zero downtime

## Support

For issues with:
- **Render Platform**: Check Render documentation
- **Google Calendar API**: Check Google Cloud Console
- **Database**: Check Neon/Supabase documentation
- **Application**: Check application logs in Render dashboard
