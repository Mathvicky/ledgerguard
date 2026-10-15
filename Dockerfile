FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 LEDGERGUARD_DB=/data/ledgerguard.db
WORKDIR /app
COPY ledgerguard ./ledgerguard
COPY web ./web
RUN useradd -u 10001 app && mkdir /data && chown app /data
USER 10001
EXPOSE 8091
CMD ["python","-m","ledgerguard.server"]
