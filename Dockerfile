FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
EXPOSE 10000
CMD ["python", "-m", "uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "10000"]
