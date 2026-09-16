FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
# The persisted vector store must be mounted or copied in at build/run time --
# it is produced by notebooks/rag_pipeline.ipynb, not by this image.
COPY data/vector_store/ ./data/vector_store/

ENV USE_TF=0
ENV TRANSFORMERS_NO_TF=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
