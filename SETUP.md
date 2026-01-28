# LightRAG Deployment Guide

This guide provides instructions for deploying and managing the LightRAG instance on the server.

## 1. Environment Configuration

Ensure your `.env` file is properly configured. Key settings include:

```bash
# Server Port
PORT=18621

# LLM Configuration
LLM_BINDING=openai
LLM_MODEL=gpt-4o-mini
LLM_BINDING_API_KEY=your_openai_api_key

# Security (Recommended for Production)
LIGHTRAG_API_KEY=your_secure_api_key
```

## 2. Deployment Commands

Run these commands from the project root directory (`~/work/minhbc/LightRAG`):

### Build the Image

Build the Docker image with the project-specific name (`lightrag`):

```bash
docker compose build
```

### Start the Service

Run the container in detached mode:

```bash
docker compose up -d
```

### Stop the Service

```bash
docker compose down
```

## 3. Monitoring and Logs

### View Logs

Thanks to the unified logging system and `FORCE_COLOR=1`, the logs are color-coded for easy reading:

```bash
docker compose logs -f lightrag
```

### Check Container Status

```bash
docker ps | grep lightrag
```

## 4. Resource Management

- **Storage**: Data is persisted in `./data/rag_storage` on the host machine.
- **Inputs**: Place documents to be scanned in `./data/inputs`.
- **API Access**:
  - WebUI: `http://<server-ip>:18621/webui`
  - API Docs: `http://<server-ip>:18621/docs`

## 5. Maintenance

### Rebuild and Restart

If you modify any Python files or settings:

```bash
docker compose down
docker compose build
docker compose up -d
```
