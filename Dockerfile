FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/documents

CMD ["uvicorn", "src.rotary_archiv.main:app", "--host", "0.0.0.0", "--port", "8000"]