# Railway Deployment Quick Start

This project is ready to deploy to Railway! Follow these steps:

## Quick Deploy Steps

1. **Push your code to GitHub** (if not already done)

2. **Create Railway Project:**
   - Go to [railway.app](https://railway.app) and sign in
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Set Environment Variables:**
   In Railway dashboard → Variables tab, add:
   ```
   MONGO_DB_CONNECTION_STRING=your_mongodb_connection_string
   SOCKETIO_ASYNC_MODE=threading
   ```

4. **Deploy:**
   - Railway will automatically detect the `Procfile` and start deploying
   - Wait for the build to complete
   - Your app will be live at the provided Railway URL

## Required Environment Variables

- `MONGO_DB_CONNECTION_STRING` (Required): Your MongoDB connection string
- `SOCKETIO_ASYNC_MODE` (Optional): Set to `threading` (default)

## Optional Environment Variables

- `GUNICORN_WORKERS`: Number of worker processes (defaults to 2 on Railway to prevent memory issues)
- `GUNICORN_THREADS`: Threads per worker (defaults to 2)
- `GUNICORN_LOG_LEVEL`: Log level - `debug`, `info`, `warning`, `error` (defaults to `info`)
- `GUNICORN_MAX_REQUESTS`: Max requests per worker before restart (defaults to 1000, helps prevent memory leaks)

## What's Configured

✅ `Procfile` - Defines the web process  
✅ `railway.json` - Railway-specific configuration  
✅ `gunicorn_config.py` - Updated to use Railway's PORT variable  
✅ `.railwayignore` - Excludes unnecessary files from deployment  
✅ `requirements.txt` - Updated with version pins

## Testing Locally with Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Set environment variables
railway variables set MONGO_DB_CONNECTION_STRING=your_connection_string

# Deploy
railway up
```

## Troubleshooting

- **Build fails**: Check that all dependencies in `requirements.txt` are valid
- **App crashes on start**: Verify `MONGO_DB_CONNECTION_STRING` is set correctly
- **Socket.IO not working**: Ensure `SOCKETIO_ASYNC_MODE=threading` is set
- **Port errors**: Railway automatically sets PORT, no manual configuration needed
- **SIGKILL / Out of Memory errors**: 
  - Set `GUNICORN_WORKERS=1` or `GUNICORN_WORKERS=2` in Railway environment variables
  - Reduce `GUNICORN_THREADS=1` if still having issues
  - Consider upgrading your Railway plan for more memory
  - The default is now 2 workers, but you can reduce to 1 if needed

## Viewing Logs

- In Railway dashboard: Go to your service → Logs tab
- Using CLI: `railway logs`

For more detailed information, see `DEPLOYMENT.md`.

