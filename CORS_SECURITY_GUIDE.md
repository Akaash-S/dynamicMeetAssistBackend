# CORS Security Configuration Guide

## Overview
This guide explains the secure CORS (Cross-Origin Resource Sharing) configuration for the AI Meeting Assistant backend.

## Security Features

### Environment-Based Configuration
- **Development**: Allows localhost and development origins automatically
- **Production**: Requires explicit CORS_ORIGINS environment variable
- **Security**: Never allows wildcard (*) in production

### Origin Validation
- Validates origin format (scheme, domain, no path/query)
- Supports both HTTP and HTTPS origins
- Rejects malformed or suspicious origins

## Configuration

### Environment Variables

#### Required for Production
```bash
# Set your frontend domains (comma-separated, no spaces)
CORS_ORIGINS=https://your-frontend-domain.com,https://your-app.vercel.app,https://your-app.netlify.app
```

#### Development (Optional)
```bash
# Can be left empty - localhost will be allowed automatically
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Security Rules

1. **Production Requirements**:
   - `CORS_ORIGINS` MUST be set
   - No wildcard (*) allowed
   - Only HTTPS origins recommended
   - Specific domains only

2. **Development Flexibility**:
   - Localhost automatically allowed
   - Wildcard allowed if no CORS_ORIGINS set
   - HTTP origins allowed for local development

## API Endpoints

### CORS Debug Endpoints (Development Only)

#### Get CORS Configuration
```bash
GET /api/cors/debug
```
Returns current CORS configuration and validation status.

#### Validate CORS Configuration
```bash
GET /api/cors/validate
```
Validates CORS configuration and returns security recommendations.

#### Test CORS with Request
```bash
GET /api/cors/test
POST /api/cors/test
OPTIONS /api/cors/test
```
Tests CORS configuration with the current request origin.

## Security Best Practices

### Production Deployment

1. **Set Specific Origins**:
   ```bash
   CORS_ORIGINS=https://myapp.com,https://www.myapp.com,https://staging.myapp.com
   ```

2. **Use HTTPS Only**:
   - Avoid HTTP origins in production
   - Include both www and non-www versions if needed

3. **No Trailing Slashes**:
   - Correct: `https://myapp.com`
   - Incorrect: `https://myapp.com/`

4. **Regular Validation**:
   - Test CORS configuration with your frontend
   - Monitor for CORS errors in logs
   - Update origins when adding new domains

### Development Setup

1. **Local Development**:
   ```bash
   # Optional - localhost is allowed automatically
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

2. **Testing**:
   - Use debug endpoints to validate configuration
   - Test with different origins
   - Verify preflight requests work

## Troubleshooting

### Common Issues

#### 1. CORS Error: "Access to fetch at '...' from origin '...' has been blocked"
**Solution**: Add your frontend domain to `CORS_ORIGINS`

#### 2. Preflight Request Fails
**Solution**: Check that your origin is in the allowed list and properly formatted

#### 3. Production Deployment Fails
**Solution**: Ensure `CORS_ORIGINS` is set with your production domains

### Debug Steps

1. **Check Configuration**:
   ```bash
   curl https://your-backend.com/api/cors/debug
   ```

2. **Validate Origins**:
   ```bash
   curl https://your-backend.com/api/cors/validate
   ```

3. **Test Specific Origin**:
   ```bash
   curl -H "Origin: https://your-frontend.com" https://your-backend.com/api/cors/test
   ```

## Environment-Specific Examples

### Development
```bash
# .env file
FLASK_ENV=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Staging
```bash
# Render environment variables
FLASK_ENV=production
CORS_ORIGINS=https://staging.myapp.com,https://staging-admin.myapp.com
```

### Production
```bash
# Render environment variables
FLASK_ENV=production
CORS_ORIGINS=https://myapp.com,https://www.myapp.com,https://admin.myapp.com
```

## Security Considerations

### What's Protected
- **Origin Validation**: Only allowed origins can make requests
- **Method Restrictions**: Only specific HTTP methods allowed
- **Header Validation**: Only specific headers allowed
- **Credential Security**: Credentials not allowed in CORS requests

### Security Headers
```http
Access-Control-Allow-Origin: https://your-frontend.com
Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS,PATCH
Access-Control-Allow-Headers: Content-Type,Authorization,X-Requested-With,Accept,Origin,X-API-Key,X-CSRFToken
Access-Control-Allow-Credentials: false
Access-Control-Max-Age: 86400
Vary: Origin
```

## Monitoring

### Health Checks
- CORS configuration is validated on startup
- Invalid configuration prevents application startup in production
- Debug endpoints available in development

### Logging
- CORS errors are logged with origin information
- Failed origin attempts are tracked
- Configuration changes are logged

## Migration Guide

### From Wildcard to Specific Origins

1. **Identify Frontend Domains**:
   - List all domains that need access
   - Include staging and production domains
   - Test each domain

2. **Update Environment Variables**:
   ```bash
   # Old (insecure)
   CORS_ORIGINS=*
   
   # New (secure)
   CORS_ORIGINS=https://myapp.com,https://www.myapp.com,https://staging.myapp.com
   ```

3. **Test Configuration**:
   - Use debug endpoints to validate
   - Test with each frontend domain
   - Monitor for CORS errors

### From Development to Production

1. **Set Production Environment**:
   ```bash
   FLASK_ENV=production
   ```

2. **Configure Origins**:
   ```bash
   CORS_ORIGINS=https://your-production-domain.com
   ```

3. **Deploy and Test**:
   - Deploy to production
   - Test CORS with production frontend
   - Monitor logs for CORS issues

## Support

For CORS-related issues:
1. Check the debug endpoints in development
2. Verify environment variables are set correctly
3. Test with your specific frontend domains
4. Check application logs for CORS errors
5. Ensure origins are properly formatted (no trailing slashes, correct protocol)
