FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先安裝套件，程式修改時可沿用這一層的快取
COPY webServer/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# core/config.py 以 /app 為基準尋找 webClient/www（頁面樣板與靜態檔案），所以兩個資料夾都放在 /app 底下
COPY webServer/ ./webServer/
COPY webClient/www/ ./webClient/www/

# 以非 root 使用者執行
RUN useradd --create-home --uid 1000 app
USER app

WORKDIR /app/webServer
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
