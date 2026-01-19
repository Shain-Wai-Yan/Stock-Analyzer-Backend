# Free Backend Deployment Guide

## Cost: $0.00/month ✅

### Step 1: Get Free API Keys (5 minutes)

1. **Alpaca Markets** (Free Paper Trading)
   - Go to: https://alpaca.markets
   - Sign up (free)
   - Create API keys (Paper Trading)
   - Copy API Key + Secret

2. **Groq** (Free AI)
   - Go to: https://console.groq.com
   - Sign up (free)
   - Create API key
   - Copy API Key

### Step 2: Deploy Backend (10 minutes)

**Option A: Fly.io (Recommended - Always Free)**

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy (from backend folder)
cd backend
fly launch --name your-app-name

# Set environment variables
fly secrets set ALPACA_API_KEY=your_key
fly secrets set ALPACA_API_SECRET=your_secret
fly secrets set GROQ_API_KEY=your_key

# Deploy
fly deploy
```

Your API: `https://your-app-name.fly.dev`

**Option B: Railway.app (Also Free)**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
cd backend
railway init
railway up

# Set env vars in Railway dashboard
```

**Option C: Render (Free but sleeps)**

1. Go to https://render.com
2. New > Web Service
3. Connect GitHub
4. Select backend folder
5. Add environment variables
6. Deploy

### Step 3: Connect Frontend

Update `.env.local` in your Next.js app:

```
NEXT_PUBLIC_API_URL=https://your-app-name.fly.dev
```

### Step 4: Test

Visit: `https://your-app-name.fly.dev/`

Should see:
```json
{
  "status": "running",
  "service": "Gap Analysis API"
}
```

Test gaps endpoint:
`https://your-app-name.fly.dev/api/gaps`

## Local Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your keys

# Run
python main.py
# or
uvicorn main:app --reload

# Open: http://localhost:8000
```

## Free Tier Limits

- **Fly.io**: 3 small VMs (256MB RAM each)
- **Alpaca**: Unlimited IEX data (15-min delayed)
- **Groq**: 14,400 requests/day (10 req/min)

## Architecture

```
Frontend (Vercel FREE)
    ↓
Backend (Fly.io FREE)
    ↓
Alpaca API (FREE data)
Groq API (FREE AI)
```

Total cost: **$0/month**

## Monitoring

Check your backend:
```bash
fly logs
```

Check health:
```bash
curl https://your-app-name.fly.dev/
```

## Troubleshooting

**502 Error**: Backend is starting (cold start), wait 30 seconds

**401 Error**: Check API keys in environment variables

**No data**: Make sure market is open or use paper trading data

## Next Steps

1. Deploy backend to Fly.io (5 min)
2. Get API keys (5 min)
3. Update frontend .env.local (1 min)
4. Test: npm run dev
5. Deploy frontend to Vercel (1 min)
6. **Start trading!**

Everything is free, always-on, production-ready. 🚀
