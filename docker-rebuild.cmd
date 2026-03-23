@echo off
echo 🚀 Rebuilding Airco Insights Docker containers...
echo.

echo 📋 Stopping existing containers...
docker-compose down

echo 🗑️ Removing old images...
docker-compose down --rmi all

echo 🔨 Building new images...
docker-compose build --no-cache

echo 🔧 Ensuring Docker network exists...
docker network create airco-insights_default 2>nul

echo ▶️ Starting containers...
docker-compose up -d

echo.
echo ✅ Docker rebuild complete!
echo.
echo 🌐 Services:
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   Database: http://localhost:5432
echo.
echo 📊 Check logs:
echo   docker-compose logs -f backend
echo   docker-compose logs -f frontend
echo.
pause
