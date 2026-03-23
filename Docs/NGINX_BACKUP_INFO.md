# Nginx Gateway Backup

## 📦 Backup Created
**File**: `nginx-gateway-backup.tar.gz` (19.5 MB)

## 📁 What's Included
Complete nginx-gateway configuration from `/opt/nginx-gateway/`:

### **Configuration Files:**
- `docker-compose.yml` - Main nginx container configuration
- `nginx/nginx.conf` - Global nginx configuration
- `nginx/conf.d/` - Site-specific configurations
  - `fintech.conf` - FinTech app configuration
  - `airco-secure.conf` - Airco Secure configuration
- `nginx/snippets/` - Reusable configuration snippets
- `nginx/ssl/` - SSL certificates and keys
- `logs/` - Nginx log files

### **Key Settings:**
- **Ports**: 80, 443 (shared for all projects)
- **Networks**: 
  - `airco_production_net` (Airco Secure)
  - `airco-fintech_default` (FinTech)
- **Upstreams**:
  - `fintech_frontend` → `fintech_frontend:3000`
  - `fintech_backend` → `fintech_backend:8000`
  - Airco Secure services

### **Domains Served:**
- `https://insights.theairco.ai` → FinTech
- `https://the-airco.net` → Airco Secure
- `https://test.theairco.ai` → FinTech (test)

## 🚀 How to Restore

### 1. Upload to Server:
```bash
scp nginx-gateway-backup.tar.gz root@your-server:/tmp/
```

### 2. Extract Backup:
```bash
ssh root@your-server
cd /tmp
tar -xzf nginx-gateway-backup.tar.gz -C /opt/
```

### 3. Restart Nginx:
```bash
cd /opt/nginx-gateway
docker-compose down
docker-compose up -d
```

## 🛡️ Important Notes
- This backup contains SSL certificates - keep secure
- All projects depend on this nginx gateway
- Network configuration is critical for container communication
- Contains log files - may be large

## 📊 Backup Info
- **Created**: 2026-03-09 13:12:36 UTC
- **Size**: 19.5 MB
- **Source**: Utho server (134.195.138.56)
- **Location**: `/opt/nginx-gateway/`

## 🔐 Security
- Contains SSL certificates for multiple domains
- Includes configuration for all production services
- Store in secure location
- Only restore to same server environment
