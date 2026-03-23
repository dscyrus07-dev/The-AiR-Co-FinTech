#!/bin/bash

# Airco Fintech Utho Deployment Script
# Run this script on your Utho server

echo "=========================================="
echo "Airco Fintech Deployment to Utho"
echo "Complete SBI Integration (27 files)"
echo "=========================================="

# Configuration
DEPLOY_DIR="/var/www/airco-fintech"
BACKUP_DIR="/var/backups/airco-fintech"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NGINX_CONFIG="/etc/nginx/sites-available/airco-fintech"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create backup
echo "Creating backup..."
mkdir -p $BACKUP_DIR
if [ -d "$DEPLOY_DIR" ]; then
    cp -r $DEPLOY_DIR $BACKUP_DIR/backup_$TIMESTAMP
    echo "✅ Backup created: $BACKUP_DIR/backup_$TIMESTAMP"
else
    echo "No existing deployment to backup"
fi

# Create deployment directory
echo "Creating deployment directory..."
mkdir -p $DEPLOY_DIR

# Stop existing containers
echo "Stopping existing containers..."
cd $DEPLOY_DIR 2>/dev/null
docker-compose down 2>/dev/null || echo "No containers to stop"

# Copy all files from the package
echo "Copying files..."
# SBI Integration
cp -r backend/app/services/banks/sbi $DEPLOY_DIR/backend/app/services/banks/ 2>/dev/null || echo "SBI files not found in current directory"

# Backend updates
cp backend/app/services/pipeline_orchestrator.py $DEPLOY_DIR/backend/app/services/ 2>/dev/null || echo "pipeline_orchestrator.py not found"
cp backend/requirements.txt $DEPLOY_DIR/backend/ 2>/dev/null || echo "requirements.txt not found"

# Frontend updates
cp frontend/app/page.tsx $DEPLOY_DIR/frontend/app/ 2>/dev/null || echo "page.tsx not found"
cp frontend/app/components/StepForm.tsx $DEPLOY_DIR/frontend/app/components/ 2>/dev/null || echo "StepForm.tsx not found"

# Testing tools
cp test_enhanced_sbi.py $DEPLOY_DIR/ 2>/dev/null || echo "test_enhanced_sbi.py not found"
cp analyze_sbi_pdfs.py $DEPLOY_DIR/ 2>/dev/null || echo "analyze_sbi_pdfs.py not found"

# Docker configuration
cp docker-compose.yml $DEPLOY_DIR/ 2>/dev/null || echo "docker-compose.yml not found"
cp docker-compose.prod.yml $DEPLOY_DIR/ 2>/dev/null || echo "docker-compose.prod.yml not found"

# Set permissions
echo "Setting permissions..."
chown -R www-data:www-data $DEPLOY_DIR
chmod -R 755 $DEPLOY_DIR

# Build and start containers
echo "Building and starting containers..."
cd $DEPLOY_DIR
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 15

# Check container status
echo "Checking container status..."
docker-compose -f docker-compose.prod.yml ps

# Configure Nginx (shared setup)
echo "Configuring Nginx..."
cat > $NGINX_CONFIG << EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Airco Fintech Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Airco Fintech Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Download endpoint
    location /download/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable Nginx site
ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Health check
echo "Performing health check..."
sleep 5

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running"
else
    echo "❌ Frontend failed to start"
fi

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start"
fi

# Test SBI Integration (if test file exists)
if [ -f "$DEPLOY_DIR/test_enhanced_sbi.py" ]; then
    echo "Testing SBI Integration..."
    cd $DEPLOY_DIR
    python test_enhanced_sbi.py
fi

echo "=========================================="
echo "Deployment completed!"
echo "Backup location: $BACKUP_DIR/backup_$TIMESTAMP"
echo "Deployment location: $DEPLOY_DIR"
echo "=========================================="

# Show logs
echo "Recent container logs:"
docker-compose -f docker-compose.prod.yml logs --tail=20

echo ""
echo "🎯 Next Steps:"
echo "1. Update your-domain.com in Nginx config"
echo "2. Configure SSL if needed"
echo "3. Test SBI PDF upload functionality"
echo "4. Monitor logs: docker-compose logs -f"
