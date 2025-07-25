# Use the official lightweight Python image
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install flask

ENV PORT=8080

CMD ["python", "app.py"]
