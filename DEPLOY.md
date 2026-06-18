# Deploying to Fly.io (Free Tier)

## One-Time Setup

### 1. Install flyctl
```powershell
# Windows (PowerShell as Admin)
iwr https://fly.io/install.ps1 -useb | iex
```

### 2. Sign up and log in
```bash
fly auth signup    # or: fly auth login
```

### 3. Initialize git repo
```bash
cd shashi-blog
git init
git add .
git commit -m "Initial commit: Shashi Shekhar AI Blog"
```

### 4. Create the Fly.io app
```bash
fly launch --name shashi-ai-blog --region sin --no-deploy
```
> Choose "No" when asked to set up Postgres or Redis.
> If the name is taken, change `app` in fly.toml to something unique like `shashi-shekhar-blog`.

### 5. Deploy
```bash
fly deploy
```

### 6. Open your site
```bash
fly open
# → https://shashi-ai-blog.fly.dev
```

---

## Adding New Blog Posts

Just create a new Markdown file in `content/posts/`:

```markdown
---
title: "Your Post Title"
date: "2025-06-01"
category: "LLMs"   # LLMs | GenAI | Agents | RAG | Prompt Engineering | MLOps
tags: ["tag1", "tag2"]
summary: "One paragraph summary shown in listings."
cover_gradient: "gradient-1"  # gradient-1 through gradient-6
cover_emoji: "🤖"
author: "Shashi Shekhar"
featured: false  # set true for the homepage featured slot
---

## Your Content Here

Write in Markdown. Code blocks, tables, blockquotes all supported.

```python
# Code is syntax-highlighted automatically
print("Hello, AI!")
```

```

Then redeploy:
```bash
fly deploy
```

---

## Updating the Site
```bash
# Make changes, then:
fly deploy
```

## Check Logs
```bash
fly logs
```

## Free Tier Limits
- Shared CPU, 256MB RAM — more than enough for a blog
- Machine auto-stops when idle (cold starts ~2s)
- 3 free shared VMs included in Fly.io free plan
- No credit card required for free tier

---

## Local Development
```bash
pip install -r requirements.txt
python app.py
# → http://localhost:8080
```
