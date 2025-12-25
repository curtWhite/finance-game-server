# SocketIO Background Tasks - Implementation Guide

## Overview

The BackgroundThreads module has been updated to properly handle SocketIO connections when running with Gunicorn and eventlet workers. This ensures reliable real-time communication between the server and clients.

## Key Changes

### 1. Background Thread Functions (`app/BackgroundThreads/__init__.py`)

#### Improvements:
- **Flask Application Context**: All background functions now use `with app.app_context()` to ensure database operations work correctly in background threads
- **Error Handling**: Enhanced error handling with proper logging and error emission to clients
- **Safe Socket Emission**: Added `_emit_to_room()` helper function that safely emits events with fallback mechanisms
- **Logging**: Added comprehensive logging for debugging and monitoring

#### Functions Updated:
- `async_apply_and_hire()`: Job application processing
- `bg_payment()`: Bank payment processing
- `bg_update_liability()`: Balance sheet liability updates

### 2. Route Updates

#### `app/Routes/Bank/route.py`
- Changed from `threading.Thread` to `socketio.start_background_task()`
- Removed unused `Thread` import

#### `app/Routes/BalanceSheet/route.py`
- Changed from `threading.Thread` to `socketio.start_background_task()`
- Removed unused imports
- Updated response message to indicate background processing

#### `classes/Job/index.py`
- Changed from `threading.Thread` to `socketio.start_background_task()`
- Removed unused `threading` import
- Added `socketio` import

## Why These Changes Matter

### Compatibility with Gunicorn + Eventlet

When using Gunicorn with eventlet workers:
- Standard Python `threading.Thread` doesn't work well with eventlet's green threads
- `socketio.start_background_task()` uses eventlet's async capabilities properly
- Ensures SocketIO events are emitted correctly across worker processes

### Flask Application Context

Background threads don't automatically have Flask's application context:
- Database operations require the app context
- Using `with app.app_context()` ensures all DB calls work correctly
- Prevents "Working outside of application context" errors

### Error Handling

Improved error handling ensures:
- Clients receive error notifications via SocketIO
- Errors are logged for debugging
- Application continues running even if background tasks fail

## SocketIO Event Structure

All background tasks emit events with this structure:

**Success:**
```json
{
  "username": "player_username",
  "message": "Success message",
  "payload": { /* relevant data */ }
}
```

**Error:**
```json
{
  "username": "player_username",
  "error": "Error message",
  "success": false,
  "message": "User-friendly error message"
}
```

## Event Names

- `job_application_complete`: Emitted when job application processing finishes
- `payment_complete`: Emitted when bank payment processing finishes
- `liabilities_offset_complete`: Emitted when liability updates finish

## Room-Based Messaging

All events are emitted to rooms based on the player's username:
- Room name: `player.username`
- Ensures only the relevant player receives their updates
- Clients must join their username room to receive events

## Testing

To test the background tasks:

1. **Job Application:**
   ```bash
   POST /api/jobs/apply
   # Client should listen for 'job_application_complete' event
   ```

2. **Bank Payment:**
   ```bash
   POST /api/bank/<username>/make_payment
   # Client should listen for 'payment_complete' event
   ```

3. **Liability Update:**
   ```bash
   POST /api/balancesheet/<username>/liability/update
   # Client should listen for 'liabilities_offset_complete' event
   ```

## Client-Side Example

```javascript
// Connect to SocketIO
const socket = io('http://your-server:5000');

// Join your username room
socket.emit('join_room', { room: 'your_username' });

// Listen for job application completion
socket.on('job_application_complete', (data) => {
  if (data.error) {
    console.error('Job application failed:', data.error);
  } else {
    console.log('Job application successful:', data.payload);
  }
});

// Listen for payment completion
socket.on('payment_complete', (data) => {
  if (data.error) {
    console.error('Payment failed:', data.error);
  } else {
    console.log('Payment successful:', data.payload);
  }
});

// Listen for liability updates
socket.on('liabilities_offset_complete', (data) => {
  if (data.error) {
    console.error('Liability update failed:', data.error);
  } else {
    console.log('Liabilities updated:', data.payload);
  }
});
```

## Monitoring

Check logs for background task activity:
- Success: `INFO` level logs with task completion
- Errors: `ERROR` level logs with full stack traces
- Socket emissions: `INFO` level logs showing event emissions

## Future Improvements

Consider:
- Adding retry logic for failed operations
- Implementing task queues (Celery, RQ) for more complex workflows
- Adding metrics/monitoring for background task performance
- Implementing task cancellation/timeout mechanisms

