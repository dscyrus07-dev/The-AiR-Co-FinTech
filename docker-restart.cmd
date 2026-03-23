@echo off
echo 🔄 Restarting Airco Insights Docker containers...
echo.

echo 📋 Stopping containers...
docker-compose down

echo 🔧 Ensuring Docker network exists...
docker network create airco-insights_default 2>nul

echo ▶️ Starting containers...
docker-compose up -d

echo.
echo ✅ Docker restart complete!
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
echo 🧹 Clean temp files:
echo   docker-compose exec backend rm -rf temp/*.xlsx
echo.
pause
