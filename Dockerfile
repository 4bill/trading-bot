FROM python:3.11-slim

RUN useradd -m -u 1000 user && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

USER user
WORKDIR /home/user

RUN git clone https://github.com/4bill/trading-bot.git app
WORKDIR /home/user/app

RUN pip install --no-cache-dir --user -r requirements.txt

ENV PATH="/home/user/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=7860

EXPOSE 7860

CMD ["python", "app.py"]
