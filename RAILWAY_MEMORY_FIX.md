# Fixing Railway Memory Issues (SIGKILL Errors)

If you're seeing `[ERROR] Worker (pid:XX) was sent SIGKILL! Perhaps out of memory?`, follow these steps:

## Quick Fix

1. **Go to Railway Dashboard** → Your Project → Variables

2. **Add/Update these environment variables:**
   ```
   GUNICORN_WORKERS=1
   GUNICORN_THREADS=2
   ```

3. **Redeploy** - Railway will automatically redeploy when you save variables

## Why This Happens

Railway's free/hobby plans typically have 512MB-1GB of RAM. Each Gunicorn worker loads:
- The entire Flask application
- MongoDB connection
- All Python classes and dependencies
- Socket.IO handlers

With the default `CPU count * 2 + 1` workers, you can easily exceed memory limits.

## Recommended Settings by Plan

### Free/Hobby Plan (512MB-1GB RAM)
```
GUNICORN_WORKERS=1
GUNICORN_THREADS=2
```

### Developer Plan (2GB RAM)
```
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
```

### Pro Plan (4GB+ RAM)
```
GUNICORN_WORKERS=2-4
GUNICORN_THREADS=2-4
```

## Additional Optimizations

If you still have memory issues with 1 worker:

1. **Reduce threads:**
   ```
   GUNICORN_WORKERS=1
   GUNICORN_THREADS=1
   ```

2. **Enable worker recycling** (prevents memory leaks):
   ```
   GUNICORN_MAX_REQUESTS=500
   GUNICORN_MAX_REQUESTS_JITTER=50
   ```

3. **Upgrade your Railway plan** for more memory

## Verify It's Working

After redeploying, check Railway logs:
- No more SIGKILL errors
- Workers stay alive
- Application responds normally

## Current Configuration

The `gunicorn_config.py` now defaults to **2 workers** which is safer, but you can override with environment variables as shown above.

