FROM mashrequae.azurecr.io/chatapi-baseimage:v1

WORKDIR /app

COPY requirements.txt .
COPY pipeline_mapping.json .
COPY app.py .
COPY ai_extractor.py .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
