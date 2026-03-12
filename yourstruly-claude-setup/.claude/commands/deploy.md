# /deploy — Deployment to AWS EC2 + Vercel

## Purpose
Step-by-step deployment checklist for pushing YoursTruly to production.

## Backend — AWS EC2 (Mumbai)

### Pre-Deploy Checks
- [ ] All tests passing locally
- [ ] .env.example updated with any new variables
- [ ] requirements.txt updated
- [ ] No hardcoded credentials in any file
- [ ] Port confirmed as 8002 in docker-compose.yml

### Deploy Steps
```bash
# 1. SSH into EC2
ssh -i your-key.pem ec2-user@YOUR_EC2_IP

# 2. Navigate to project
cd /home/ec2-user/yourstruly-intelligence

# 3. Pull latest from main
git pull origin main

# 4. Update .env if new variables added
nano .env

# 5. Rebuild and restart container
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 6. Check container is running
docker ps | grep yourstruly

# 7. Check logs for startup errors
docker logs yourstruly-api --tail=50

# 8. Test health endpoint
curl http://localhost:8002/health
```

### Verify Running
```bash
# Should return {"status": "healthy", "version": "x.x.x"}
curl http://localhost:8002/health

# Test orders endpoint
curl http://localhost:8002/api/dashboard/revenue?date=2026-03-10
```

## Frontend — Vercel

### Vercel deploys automatically on push to main.
No manual steps needed if GitHub → Vercel integration is configured.

### Manual deploy if needed:
```bash
cd frontend
npx vercel --prod
```

### Environment Variables on Vercel
Set these in Vercel dashboard → Project Settings → Environment Variables:
- `VITE_API_URL` = `http://YOUR_EC2_IP:8002`

## GitHub Actions (CI/CD)
The `.github/workflows/deploy.yml` runs on every push to main:
1. Runs Python tests
2. SSHs into EC2
3. Pulls latest code
4. Rebuilds Docker container
5. Vercel auto-deploys frontend

## Rollback
```bash
# On EC2 — rollback to previous Docker image
docker-compose down
git checkout HEAD~1
docker-compose build
docker-compose up -d
```
