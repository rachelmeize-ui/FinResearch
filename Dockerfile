FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FINRESEARCH_BIND=0.0.0.0 PORT=10000 FINRESEARCH_DATA_DIR=/var/lib/finresearch FINRESEARCH_EXCEL_BACKEND=portable
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 finresearch && mkdir -p /var/lib/finresearch && chown finresearch /var/lib/finresearch
COPY --chown=finresearch:finresearch *.py ./
COPY --chown=finresearch:finresearch static ./static
COPY --chown=finresearch:finresearch docs ./docs
USER finresearch
EXPOSE 10000
CMD ["python", "server.py"]
