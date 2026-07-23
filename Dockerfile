FROM python:3.11.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
COPY app ./app
COPY data ./data
COPY config.yaml ./
COPY .streamlit ./.streamlit

RUN pip install --upgrade pip && pip install .

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"
CMD ["streamlit", "run", "app/Home.py", "--server.address=0.0.0.0", "--server.port=8501"]
