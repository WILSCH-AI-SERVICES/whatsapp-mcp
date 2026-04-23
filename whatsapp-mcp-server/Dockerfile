FROM python:3.11-slim
RUN pip install --no-cache-dir uv
WORKDIR /app/whatsapp-mcp-server
COPY pyproject.toml ./
RUN uv sync
COPY . .
EXPOSE 8090
CMD ["uv", "run", "main.py"]
