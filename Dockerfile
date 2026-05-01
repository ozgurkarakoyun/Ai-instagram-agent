FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    libcairo2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads output static/fonts

CMD python -c "import os,subprocess; subprocess.run(['uvicorn','main:app','--host','0.0.0.0','--port',os.environ.get('PORT','8080')])"
