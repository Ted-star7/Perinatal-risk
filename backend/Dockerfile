FROM python:3.12-slim

WORKDIR /code
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/code

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

COPY backend/app ./app
COPY backend/evaluations ./evaluations
COPY ml ./ml
COPY contracts ./contracts
COPY backend/models ./model-release
RUN python -m ml.src.package_release --install model-release/antenatal-release.tar.gz

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
