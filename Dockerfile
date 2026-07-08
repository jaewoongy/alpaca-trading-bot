FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY trading_mcp_server.py pipeline.py watchlist.json ./
COPY signals ./signals

EXPOSE 8000

CMD ["python", "trading_mcp_server.py"]
