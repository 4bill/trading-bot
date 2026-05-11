FROM python:3.11

WORKDIR /app

# HF Spaces requires the container to run as a non-root user with UID 1000.
RUN useradd -m -u 1000 user

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

USER user

ENV PORT=7860 \
    PYTHONUNBUFFERED=1
EXPOSE 7860

CMD ["python", "app.py"]
