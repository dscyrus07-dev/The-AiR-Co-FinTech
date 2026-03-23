---
description: How to deploy updates to a Utho VPS with Docker and Nginx Gateway via SCP
---
# Deployment Workflow (Utho VPS)

This workflow provides a step-by-step guide to deploying a containerized project (like FinTech SAAS) to a Utho VPS server, utilizing an external Nginx gateway. 

It explicitly focuses on **incremental deployments** (uploading only changed files) to save bandwidth and time, and to avoid downtime or interference with other running applications on the server (e.g., Airco Secure).

## Prerequisites
- SSH access to the Utho VPS.
- `scp` (Secure Copy Protocol) available on your local Windows terminal.
- Docker and Docker Compose installed on the Utho server.
- Existing `nginx-gateway` reverse-proxy container running on a shared Docker network (e.g., `production_net`).

---

## 1. Local Development Workflow
Before deploying, ensure your local changes work properly:
1. Test your code locally (`npm run dev` or `docker-compose up`).
2. Verify all syntax/linting errors are resolved.
3. Track exactly which files or folders were modified. For example, if you updated the backend reporting logic and frontend result UI, you only need to sync those precise elements over `scp`.

---

## 2. Upload Only Changed Files (via `scp`)
To avoid uploading the entire project (which includes large `node_modules` or `.next` folders), use `scp` to target only the modified files from your **local terminal**.

### Example Commands (Run locally)
```bash
# Uploading a specific backend python file
scp "backend/app/routers/upload.py" root@<UTHO_SERVER_IP>:/path/to/project/backend/app/routers/upload.py

# Uploading a specific frontend component
scp "frontend/app/components/ResultStep.tsx" root@<UTHO_SERVER_IP>:/path/to/project/frontend/app/components/ResultStep.tsx

# Uploading an entire newly updated directory (recursive)
scp -r "backend/app/services/banks/" root@<UTHO_SERVER_IP>:/path/to/project/backend/app/services/
```

---

## 3. SSH into the Utho VPS
Once the files are uploaded, open a persistent terminal connection to the server.
```bash
ssh root@<UTHO_SERVER_IP>
```

---

## 4. Navigate to the Target Project Directory
Once logged in, navigate into the directory holding your `docker-compose.yml` file. 
> **Note:** Ensure you navigate strictly into the target project (e.g., `/var/www/fintech-saas`), avoiding the `airco-secure` directory to not disrupt it.
```bash
cd /path/to/project
```

---

## 5. Stop Current Containers
Stop the old running containers for the specific project so Docker can rebuild the fresh changes.
```bash
docker-compose down
```

> **Warning: `network has active endpoints`**
> Because this project's containers share a network with the external `nginx-gateway` container, you will likely see an error saying Docker failed to remove the network because it has "active endpoints". 
> **This is 100% normal and can be safely ignored.** Docker leaves the network intact so the untouched `nginx-gateway` stays running for your other live projects.

---

## 6. Rebuild Docker Images (`--no-cache`)
Now, force Docker to recompile the project images from scratch to absorb the new files you fed in via `scp`.

**Rebuild Everything:**
```bash
docker-compose build --no-cache
```

**Rebuild Specific Services (Recommended for Speed):**
If you only uploaded a frontend component, you only need to rebuild the frontend container:
```bash
# Rebuild frontend service
docker-compose build --no-cache frontend

# Rebuild backend / API service
docker-compose build --no-cache backend

# Rebuild ML pipeline service (if applicable)
docker-compose build --no-cache ml-pipeline
```

---

## 7. Start Containers
Turn the newly built containers back on in detached mode.
```bash
docker-compose up -d
```

---

## 8. Restart the Nginx Gateway
Refresh your reverse proxy container so it correctly re-acquires the backend and frontend Docker internal IP mappings, enforcing successful public SSL resolution. This is extremely important if `docker-compose down` dropped internal DNS.
```bash
docker restart nginx-gateway
```

---

## 9. Verify the Deployment
Ensure the new containers are healthy and accessible.

**Check Up/Running Status:**
```bash
docker-compose ps
```

**Monitor Application Logs for Errors:**
```bash
# Check Backend API logstream
docker logs -f <backend_container_name>  # e.g., fintech-backend-1

# Check Frontend logstream
docker logs -f <frontend_container_name> # e.g., fintech-frontend-1
```
*(Press `Ctrl+C` to exit the log viewer).*
