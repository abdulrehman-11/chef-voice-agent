# Deployment Guide - Vercel + Railway

## Architecture

```
Frontend (Vercel) → Token Server (Railway) → LiveKit Agent (Railway)
                                           ↓
                                    Database (NeonDB)
                                           ↓
                                    Google Sheets
```

## Step 1: Prepare Repository

1. **Stop duplicate processes**:
   ```powershell
   Get-Process python | Stop-Process -Force
   ```

2. **Initialize git** (if not done):
   ```bash
   cd "C:\Users\hp\Documents\Antigravity\Cooking voice Ai agent"
   git init
   git add .
   git commit -m "Initial commit - Chef Voice AI Agent"
   ```

3. **Push to GitHub**:
   ```bash
   git remote add origin https://github.com/abdulrehman-11/chef-voice-agent.git
   git branch -M main
   git push -u origin main
   ```

---

## Step 2: Deploy Backend to Railway

### 2.1 Connect to Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `chef-voice-agent`
4. Railway will detect Python automatically

### 2.2 Configure Environment Variables

In Railway dashboard, add these variables:

```bash
# LiveKit
LIVEKIT_URL=wss://chef-live-voice-agent-n6istvo9.livekit.cloud
LIVEKIT_API_KEY=APImtPKEaK5sy8S
LIVEKIT_API_SECRET=W122Zk6Eee4MWNzXzDMlk542MJfMkmzEWjdWSEq0ficD

# AI Services
DEEPGRAM_API_KEY=9089888cd2c6cf8caaec3647c0cfef484c082f98
CARTESIA_API_KEY=sk_car_AgBBX5wDATNUePak3xy5b2
GROQ_API_KEY=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
GROQ_MODEL=llama-3.1-8b-instant

# Database
DATABASE_URL=postgresql://neondb_owner:npg_zLiK0uGmZfd5@ep-raspy-art-ahleesnt-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# Google Sheets (upload hexaa-clinic-calendar-d10d149802d7.json separately)
GOOGLE_SHEETS_SPREADSHEET_ID=1xM53vaaJ7-eY1X0KboKmgy6kIdkVMmeBwnbMX-Ic23A
```

### 2.3 Upload Google Credentials

1. In Railway, go to your service
2. Click "Variables" → "Add Secret File"
3. Name: `GOOGLE_SHEETS_CREDENTIALS`
4. Upload: `hexaa-clinic-calendar-d10d149802d7.json`

### 2.4 Set Root Directory

Railway Settings:
- **Root Directory**: `backend`
- **Start Command**: `python start_production.py`

### 2.5 Deploy

Railway will:
1. Install dependencies from `requirements.txt`
2. Start the agent
3. Provide a public URL like: `https://chef-voice-agent-production.up.railway.app`

**Save this URL - you'll need it for Vercel!**

---

## Step 3: Deploy Frontend to Vercel

### 3.1 Connect to Vercel

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import `chef-voice-agent` from GitHub
4. **Root Directory**: Set to `frontend-improved`

### 3.2 Configure Environment Variables

In Vercel dashboard:

```bash
VITE_TOKEN_SERVER_URL=https://chef-voice-agent-production.up.railway.app/get-token
```

Replace with your actual Railway URL from Step 2.5.

### 3.3 Deploy

Vercel will:
1. Build static frontend
2. Deploy to CDN
3. Provide URL like: `https://chef-voice-agent.vercel.app`

---

## Step 4: Update Frontend Config

The frontend needs to use the Railway URL. Since we're using static hosting, we'll use a simple approach:

**Edit `frontend-improved/app.js` line ~15:**

Change:
```javascript
const TOKEN_SERVER_URL = 'http://localhost:5000/get-token';
```

To:
```javascript
const TOKEN_SERVER_URL = 'https://YOUR-RAILWAY-URL.up.railway.app/get-token';
```

Then:
```bash
git add frontend-improved/app.js
git commit -m "Update to production API endpoint"
git push
```

Vercel will auto-redeploy.

---

## Step 5: Test Production

1. **Open frontend**: `https://chef-voice-agent.vercel.app`
2. **Click "Start Creating"**
3. **Click mic button**
4. **Say**: "Hi TULLIA, create a batch recipe called Test Sauce"
5. **Verify**: Check Google Sheets for the new recipe

---

## Troubleshooting

### ❌ "Failed to connect"
- Check Railway logs: Are services running?
- Check CORS: Railway should allow Vercel domain

### ❌ "Rate limit exceeded"
- Groq free tier hit
- Switch to `llama-3.1-8b-instant` in Railway env vars

### ❌ "Database connection failed"
- Verify `DATABASE_URL` in Railway
- Check NeonDB is active

---

## Environment Summary

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | `https://chef-voice-agent.vercel.app` |
| Backend | Railway | `https://chef-voice-agent-production.up.railway.app` |
| Database | NeonDB | PostgreSQL (already configured) |
| LiveKit | LiveKit Cloud | `wss://chef-live-voice-agent-n6istvo9.livekit.cloud` |

---

## Cost Estimate

- **Vercel**: Free (hobby plan)
- **Railway**: ~$5/month (500h free/month, then $0.000231/min)
- **NeonDB**: Free (512MB storage, 0.5GB RAM)
- **LiveKit Cloud**: Free (100 concurrent participants)
- **Groq**: Free (100k tokens/day) or $0.59/1M tokens
- **Deepgram**: Pay as you go ($0.0043/min)
- **Cartesia**: Pay as you go (~$0.06/1k chars)

**Monthly estimate**: $10-30 depending on usage

---

## Next Steps After Deployment

1. Test all recipe operations (save, search, update, delete)
2. Monitor Railway logs for errors
3. Set up monitoring/alerting
4. Add custom domain (optional)
5. Enable Vercel Analytics (optional)
