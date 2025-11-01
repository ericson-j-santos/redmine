# Redmine Deployment Guide

## ⚠️ Important: Vercel Compatibility Issue

**This Redmine installation is currently showing a "Page not found" error on Vercel because Vercel is not designed to host traditional Ruby on Rails applications.**

### Why doesn't it work on Vercel?

Vercel is optimized for:
- ✅ Static sites (HTML, CSS, JavaScript)
- ✅ Next.js, React, Vue applications
- ✅ Serverless functions (Node.js, Go, Python, Ruby functions)

Redmine requires:
- ❌ Persistent application server (Puma, Unicorn)
- ❌ Database server (MySQL, PostgreSQL, SQLite)
- ❌ File storage and background jobs
- ❌ Long-running Ruby process

## 🚀 Recommended Hosting Platforms

Here are the best platforms to deploy Redmine:

### 1. **Heroku** (Easiest)
Perfect for Rails apps with free/paid tiers.

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login and create app
heroku login
heroku create your-redmine-app

# Add database
heroku addons:create heroku-postgresql:mini

# Deploy
git push heroku master

# Run migrations
heroku run rails db:migrate

# Visit your app
heroku open
```

**Pros:** Simple deployment, managed database, automatic SSL
**Cons:** Paid plans for production use

### 2. **Railway** (Modern & Simple)
Modern platform with excellent Rails support.

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Visit dashboard to configure database
```

**Pros:** Great developer experience, free tier available
**Cons:** Relatively new platform

### 3. **Render** (Free Tier Available)
Good alternative with free tier.

1. Create account at [render.com](https://render.com)
2. Connect GitHub repository
3. Select "Web Service"
4. Build Command: `bundle install; bundle exec rails db:migrate`
5. Start Command: `bundle exec rails server -b 0.0.0.0 -p $PORT`

**Pros:** Free tier, automatic deployments
**Cons:** Free tier has limitations

### 4. **Fly.io** (Global Deployment)
Great for distributed apps.

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch

# Deploy
fly deploy

# Check status
fly status
```

**Pros:** Global edge deployment, generous free tier
**Cons:** Requires some configuration

### 5. **DigitalOcean App Platform**
Managed platform from DigitalOcean.

1. Create DigitalOcean account
2. Navigate to App Platform
3. Connect GitHub repository
4. Configure build and run commands
5. Deploy

**Pros:** Reliable infrastructure, good pricing
**Cons:** Requires credit card

### 6. **VPS/Cloud Server** (Advanced)
Full control with VPS (DigitalOcean, Linode, AWS EC2).

Requirements:
- Ruby 3.2+
- Database (MySQL/PostgreSQL)
- Web server (Nginx/Apache)
- Application server (Puma)

**Pros:** Full control, cost-effective for high traffic
**Cons:** Requires server management skills

## 🔧 Local Development Setup

To run Redmine locally for development:

### Prerequisites
- Ruby 3.2.0 or later
- Bundler
- Database (SQLite for dev, MySQL/PostgreSQL for production)
- Git

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/ericson-j-santos/redmine.git
   cd redmine
   ```

2. **Install dependencies**
   ```bash
   bundle install
   ```

3. **Configure database**
   ```bash
   # Copy example config
   cp config/database.yml.example config/database.yml
   
   # Edit config/database.yml with your database settings
   ```

4. **Create and migrate database**
   ```bash
   bundle exec rails db:create
   bundle exec rails db:migrate
   bundle exec rails redmine:load_default_data
   ```

5. **Start the server**
   ```bash
   bundle exec rails server
   ```

6. **Access Redmine**
   Open your browser to: `http://localhost:3000`
   
   Default credentials:
   - Username: `admin`
   - Password: `admin`

## 🐳 Docker Deployment

Use Docker for containerized deployment:

```bash
# Using official Redmine image
docker run -d -p 3000:3000 \
  -e REDMINE_DB_MYSQL=db \
  -e REDMINE_DB_DATABASE=redmine \
  -e REDMINE_DB_USERNAME=redmine \
  -e REDMINE_DB_PASSWORD=secret \
  --name redmine \
  redmine:latest
```

Or use Docker Compose - see `docker-compose.yml` (if available).

## 📋 Production Checklist

Before deploying to production:

- [ ] Set `RAILS_ENV=production`
- [ ] Set strong `SECRET_KEY_BASE`
- [ ] Configure production database
- [ ] Set up SSL/HTTPS
- [ ] Configure email delivery (SMTP)
- [ ] Set up backups
- [ ] Configure file storage
- [ ] Set up monitoring
- [ ] Review security settings
- [ ] Test all functionality

## 🔐 Environment Variables

Required environment variables for production:

```bash
RAILS_ENV=production
SECRET_KEY_BASE=your_secret_key_here
DATABASE_URL=postgresql://user:password@host:5432/redmine
REDMINE_DB_POSTGRES=host
REDMINE_DB_DATABASE=redmine
REDMINE_DB_USERNAME=redmine
REDMINE_DB_PASSWORD=password
```

Generate a secret key:
```bash
bundle exec rails secret
```

## 📚 Additional Resources

- [Official Redmine Installation Guide](https://www.redmine.org/projects/redmine/wiki/RedmineInstall)
- [Redmine Documentation](https://www.redmine.org/projects/redmine/wiki/Guide)
- [Ruby on Rails Deployment Guide](https://guides.rubyonrails.org/deployment.html)
- [This Repository](https://github.com/ericson-j-santos/redmine)

## 🆘 Troubleshooting

### "Page not found" error on Vercel
This is expected. Vercel cannot run Rails apps without complex serverless configuration. Use one of the recommended platforms above.

### Database connection errors
1. Check `config/database.yml` configuration
2. Ensure database server is running
3. Verify credentials are correct
4. Check network connectivity

### Assets not loading
```bash
# Precompile assets for production
RAILS_ENV=production bundle exec rails assets:precompile
```

### Migration errors
```bash
# Reset database (WARNING: deletes all data)
bundle exec rails db:reset

# Or manually run migrations
bundle exec rails db:migrate
```

## 📞 Getting Help

- **GitHub Issues**: [Open an issue](https://github.com/ericson-j-santos/redmine/issues)
- **Redmine Community**: [Redmine Forums](https://www.redmine.org/projects/redmine/boards)
- **Stack Overflow**: Tag questions with `redmine` and `ruby-on-rails`

---

**Last Updated**: November 2025  
**Redmine Version**: 6.0.x  
**Rails Version**: 8.0.x  
**Ruby Version**: 3.2.x
