# Scheduler Usage Guide

Quick reference for using the Mentor's scheduled digest generation.

## Quick Start

### 1. Enable Scheduler

Add to `apps/ai-core/.env`:
```bash
ENABLE_SCHEDULER=true
ENABLE_DAILY_DIGEST=true
DAILY_DIGEST_HOUR=7
DAILY_DIGEST_MINUTE=0
```

### 2. Start Server

```bash
cd apps/ai-core
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

### 3. Verify Scheduler is Running

```bash
curl http://localhost:8000/mentor/status | jq .scheduler
```

Expected:
```json
{
  "enabled": true,
  "running": true,
  "next_run": "2025-10-09T07:00:00Z"
}
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_SCHEDULER` | `true` | Enable/disable APScheduler |
| `ENABLE_DAILY_DIGEST` | `true` | Enable/disable daily digest generation |
| `DAILY_DIGEST_HOUR` | `7` | Hour to run (0-23) |
| `DAILY_DIGEST_MINUTE` | `0` | Minute to run (0-59) |
| `CRON_API_KEY` | `change-me-in-production` | API key for external triggers |

### Example Configurations

**Morning Digest (7:00 AM)**:
```bash
DAILY_DIGEST_HOUR=7
DAILY_DIGEST_MINUTE=0
```

**Evening Digest (6:00 PM)**:
```bash
DAILY_DIGEST_HOUR=18
DAILY_DIGEST_MINUTE=0
```

**Noon Digest**:
```bash
DAILY_DIGEST_HOUR=12
DAILY_DIGEST_MINUTE=0
```

**Every 2 hours** (requires code modification):
```python
scheduler.add_job(
    generate_daily_digest_job,
    trigger='interval',
    hours=2
)
```

## Manual Control

### Generate Digest Now

**Option 1: Standard endpoint** (no auth):
```bash
curl -X POST http://localhost:8000/mentor/generate-digest
```

**Option 2: Trigger endpoint** (with auth):
```bash
curl -X POST http://localhost:8000/mentor/trigger-daily-digest \
  -H "X-API-Key: your-api-key"
```

### Check Next Scheduled Run

```bash
curl http://localhost:8000/mentor/status | jq '.scheduler.next_run'
```

### Disable Scheduler Temporarily

Set in `.env`:
```bash
ENABLE_SCHEDULER=false
```

Then restart server.

## Monitoring

### Watch Logs

```bash
# Terminal 1: Run server
cd apps/ai-core
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Watch logs
tail -f logs/ai-core.log  # If logging to file
```

### Check for Scheduled Execution

Look for these logs around scheduled time:
```
INFO - Running scheduled daily digest generation...
INFO - Daily digest generated successfully: 3 insights created
```

### Check for Errors

```
ERROR - Error in scheduled digest generation: [error details]
```

## Troubleshooting

### Issue: Scheduler not running

**Check status**:
```bash
curl http://localhost:8000/mentor/status | jq .scheduler
```

**Possible causes**:
1. `ENABLE_SCHEDULER=false` in config
2. Server crashed during startup
3. APScheduler not installed

**Solution**:
```bash
# Check environment
echo $ENABLE_SCHEDULER

# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart server
uvicorn main:app --reload --port 8000
```

### Issue: Digest not generated at scheduled time

**Check next run time**:
```bash
curl http://localhost:8000/mentor/status | jq '.scheduler.next_run'
```

**Check server logs** for errors around scheduled time.

**Possible causes**:
1. Server was down at scheduled time
2. Error during generation
3. Timezone mismatch

**Solution**:
1. Ensure server stays running
2. Check error logs
3. Manually trigger to verify it works:
   ```bash
   curl -X POST http://localhost:8000/mentor/generate-digest
   ```

### Issue: 401 Unauthorized on trigger endpoint

**Cause**: Incorrect API key

**Solution**:
```bash
# Check your API key in .env
cat apps/ai-core/.env | grep CRON_API_KEY

# Use correct key
curl -X POST http://localhost:8000/mentor/trigger-daily-digest \
  -H "X-API-Key: change-me-in-production"
```

### Issue: Timezone issues

**Symptom**: Digest runs at wrong time

**Check server timezone**:
```bash
date
```

**Solution**: Configure timezone in cron trigger (requires code change):
```python
from apscheduler.triggers.cron import CronTrigger
import pytz

scheduler.add_job(
    generate_daily_digest_job,
    trigger=CronTrigger(
        hour=7,
        minute=0,
        timezone=pytz.timezone('America/New_York')
    )
)
```

## External Scheduler Integration

### Vercel Cron

**1. Create Vercel Cron config** (`vercel.json`):
```json
{
  "crons": [{
    "path": "/api/cron/daily-digest",
    "schedule": "0 7 * * *"
  }]
}
```

**2. Create API route** (`apps/web/app/api/cron/daily-digest/route.ts`):
```typescript
export async function GET(request: Request) {
  const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

  const response = await fetch(`${AI_CORE_URL}/mentor/trigger-daily-digest`, {
    method: 'POST',
    headers: {
      'X-API-Key': process.env.CRON_API_KEY!
    }
  });

  const result = await response.json();
  return Response.json(result);
}
```

**3. Set environment variables** in Vercel:
```bash
CRON_API_KEY=<your-secure-key>
AI_CORE_URL=https://your-ai-core.railway.app
```

**4. Disable internal scheduler**:
```bash
ENABLE_SCHEDULER=false
```

### Railway Cron

**Option 1**: Use internal scheduler (default)
- Railway keeps server running
- APScheduler handles scheduling
- No additional config needed

**Option 2**: Use Railway Cron Jobs (if available)
- Create separate cron service
- Calls trigger endpoint
- More robust for distributed deployments

### GitHub Actions

**Create workflow** (`.github/workflows/daily-digest.yml`):
```yaml
name: Daily Digest

on:
  schedule:
    - cron: '0 7 * * *'  # 7 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Daily Digest
        run: |
          curl -X POST ${{ secrets.AI_CORE_URL }}/mentor/trigger-daily-digest \
            -H "X-API-Key: ${{ secrets.CRON_API_KEY }}"
```

## Production Recommendations

### Security

1. **Generate secure API key**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set in environment** (not in .env file):
   ```bash
   export CRON_API_KEY=<generated-key>
   ```

3. **Use HTTPS** for external triggers

### Reliability

1. **Monitor scheduler status**:
   - Set up health check endpoint
   - Alert if scheduler stops running
   - Track digest generation success rate

2. **Backup trigger**:
   - Use external scheduler as backup
   - Manually trigger if automated fails
   - Keep logs for debugging

3. **Error handling**:
   - Scheduler catches errors gracefully
   - Logs full stack traces
   - Continues running after errors

### Performance

1. **Avoid peak hours** if possible:
   ```bash
   DAILY_DIGEST_HOUR=6  # Before 7 AM user traffic
   ```

2. **Monitor API costs**:
   - Each digest = 3 Claude API calls
   - ~$0.10 per day at current rates
   - Set spending limits in Anthropic dashboard

3. **Database load**:
   - Digest generation does ~10 database queries
   - Runs outside peak hours by default
   - Indexes from Phase 1 optimize queries

## Testing Checklist

Before deploying:

- [ ] Scheduler starts successfully
- [ ] Status endpoint shows correct next run time
- [ ] Manual digest generation works
- [ ] Trigger endpoint accepts correct API key
- [ ] Trigger endpoint rejects incorrect API key
- [ ] Logs show scheduled execution
- [ ] Insights appear in database after run
- [ ] UI shows new insights
- [ ] Error handling works (test with invalid data)
- [ ] Scheduler survives app restart

## Useful Commands

```bash
# Start server with scheduler
cd apps/ai-core && source venv/bin/activate && uvicorn main:app --port 8000

# Check scheduler status
curl -s http://localhost:8000/mentor/status | jq .scheduler

# Generate digest now
curl -s -X POST http://localhost:8000/mentor/generate-digest | jq

# Trigger with auth
curl -s -X POST http://localhost:8000/mentor/trigger-daily-digest \
  -H "X-API-Key: your-key" | jq

# Check recent insights
curl -s http://localhost:8000/api/insights?status=open | jq

# Watch logs (if logging to file)
tail -f logs/ai-core.log

# Test APScheduler installation
python -c "from apscheduler.schedulers.background import BackgroundScheduler; print('OK')"
```

## FAQ

**Q: Can I run multiple digests per day?**
A: Yes, but requires code modification. Add multiple jobs or use interval trigger instead of cron.

**Q: What happens if server restarts?**
A: Scheduler restarts with server. Missed runs are skipped (not caught up).

**Q: Can I customize digest content?**
A: Yes, modify prompt engineering in Phase 3 (`apps/ai-core/agents/mentor.py`).

**Q: How do I change the timezone?**
A: Configure timezone in CronTrigger (see Troubleshooting section above).

**Q: Can I disable specific insight types?**
A: Yes, modify `generate_daily_digest()` in mentor.py to skip certain types.

**Q: What if I want instant insights instead of daily?**
A: Use the manual trigger endpoint or create a real-time insight system (future enhancement).

---

For more details, see:
- `phase-6-complete.md` - Full implementation details
- `phase-6-summary.md` - Quick overview
- `implementation-plan.md` - Original plan
