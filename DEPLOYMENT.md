# Backend Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- AWS RDS PostgreSQL database configured
- AWS S3 bucket created
- Firebase project set up
- Environment variables configured

### Environment Setup

1. **Create `.env` file** in the backend directory:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Database Configuration (AWS RDS)
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_NAME=meeting_assistant
DB_USER=your-db-user
DB_PASSWORD=your-db-password

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name

# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
FROM_NAME=AI Meeting Assistant

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# AI Services
GROQ_API_KEY=your-groq-api-key
GROQ_API_KEY_FALLBACK=your-fallback-groq-key
OPENAI_API_KEY=your-openai-key

# ChromaDB Configuration
CHROMA_HOST=localhost
CHROMA_PORT=8001

# Application Configuration
WEB_CONCURRENCY=4
GUNICORN_TIMEOUT=120
PORT=8000
FRONTEND_URL=https://your-frontend-domain.com
BACKEND_URL=https://your-backend-domain.com
```

## 🐳 Docker Deployment

### Build and Run with Docker Compose

```bash
# Build the image
docker-compose build

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop the service
docker-compose down
```

### Build and Run with Docker

```bash
# Build the image
docker build -t ai-meeting-backend:latest .

# Run the container
docker run -d \
  --name ai-meeting-backend \
  -p 8000:8000 \
  --env-file .env \
  ai-meeting-backend:latest

# View logs
docker logs -f ai-meeting-backend

# Stop the container
docker stop ai-meeting-backend
docker rm ai-meeting-backend
```

## ☁️ Cloud Deployment

### AWS ECS/Fargate

1. **Push image to ECR:**
```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag the image
docker tag ai-meeting-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-meeting-backend:latest

# Push to ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-meeting-backend:latest
```

2. **Create ECS Task Definition** with environment variables from `.env`

3. **Create ECS Service** with load balancer

### Render.com

1. **Connect your repository** to Render

2. **Create a new Web Service:**
   - Environment: Docker
   - Build Command: (automatic)
   - Start Command: (uses Dockerfile CMD)

3. **Add environment variables** from your `.env` file

4. **Deploy!**

### Railway.app

1. **Connect repository** to Railway

2. **Add environment variables** in Railway dashboard

3. **Deploy** - Railway will automatically detect Dockerfile

### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ai-meeting-backend

# Deploy to Cloud Run
gcloud run deploy ai-meeting-backend \
  --image gcr.io/YOUR_PROJECT_ID/ai-meeting-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars-file .env.yaml
```

## 🔧 Production Optimizations

### Performance Tuning

**Gunicorn Workers:**
- Formula: `(2 x CPU cores) + 1`
- Set via `WEB_CONCURRENCY` environment variable
- Default: 4 workers

**Timeout Configuration:**
- Default: 120 seconds
- Adjust via `GUNICORN_TIMEOUT` for long-running requests

### Security Best Practices

1. **Use secrets management:**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Environment-specific secrets

2. **Enable HTTPS:**
   - Use reverse proxy (nginx, Caddy)
   - Configure SSL certificates
   - Force HTTPS redirects

3. **Database security:**
   - Use SSL connections to RDS
   - Rotate credentials regularly
   - Use IAM authentication when possible

4. **API rate limiting:**
   - Configure in reverse proxy
   - Use AWS API Gateway
   - Implement application-level limits

### Monitoring & Logging

**Health Checks:**
- Endpoint: `/api/health`
- Interval: 30 seconds
- Timeout: 10 seconds

**Logging:**
- Logs to stdout/stderr
- Captured by Docker logging driver
- Forward to CloudWatch, Datadog, or similar

**Metrics to Monitor:**
- Response times
- Error rates
- CPU/Memory usage
- Database connection pool
- S3 upload/download times

## 🔄 CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy Backend

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push Docker image
        working-directory: ./backend
        run: |
          docker build -t ai-meeting-backend .
          docker tag ai-meeting-backend:latest ${{ steps.login-ecr.outputs.registry }}/ai-meeting-backend:latest
          docker push ${{ steps.login-ecr.outputs.registry }}/ai-meeting-backend:latest
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster ai-meeting-cluster --service backend --force-new-deployment
```

## 🧪 Testing Deployment

```bash
# Health check
curl https://dynamicmeetassistbackend-1.onrender.com/api/health

# Test authentication
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# Check logs
docker-compose logs -f backend
```

## 📊 Scaling Considerations

### Horizontal Scaling
- Run multiple container instances
- Use load balancer (ALB, nginx)
- Session management via Redis/database

### Vertical Scaling
- Increase container CPU/memory
- Adjust worker count
- Optimize database queries

### Database Scaling
- Use RDS read replicas
- Enable connection pooling
- Implement caching (Redis)

## 🆘 Troubleshooting

### Container won't start
```bash
# Check logs
docker logs ai-meeting-backend

# Verify environment variables
docker exec ai-meeting-backend env

# Test database connection
docker exec ai-meeting-backend python -c "from config.database import init_db; init_db()"
```

### High memory usage
- Reduce worker count
- Check for memory leaks
- Monitor with `docker stats`

### Slow response times
- Check database query performance
- Monitor S3 upload/download times
- Review Gunicorn worker configuration

## 📝 Maintenance

### Database Migrations
```bash
# Run migrations
docker exec ai-meeting-backend python migrations/run_migrations.py

# Backup database
pg_dump -h your-rds-endpoint.rds.amazonaws.com -U your-user -d meeting_assistant > backup.sql
```

### Log Rotation
- Configured in docker-compose.yml
- Max size: 10MB per file
- Keep 3 files

### Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## 🔐 Security Checklist

- [ ] All secrets in environment variables (not hardcoded)
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Database uses SSL connections
- [ ] Non-root user in container
- [ ] Regular security updates applied
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Input validation enabled
- [ ] SQL injection protection active
- [ ] XSS protection enabled

## 📞 Support

For deployment issues:
- Check logs: `docker-compose logs -f`
- Review health endpoint: `/api/health`
- Contact: support@aimeetingassistant.com
