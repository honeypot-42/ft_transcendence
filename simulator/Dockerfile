FROM python:3.12-slim

# Non-root user. The log directory is created and owned by this user in the
# image, so a fresh named volume mounted on it inherits that ownership.
RUN useradd --system --uid 10001 --no-create-home simulator \
    && mkdir -p /var/log/honeypot \
    && chown simulator:simulator /var/log/honeypot

WORKDIR /app
COPY simulate_attacks.py .

USER simulator
ENV PYTHONUNBUFFERED=1 \
    SIMULATOR_MODE=basic \
    OUTPUT_FILE=/var/log/honeypot/cowrie.json

# Healthy while the log file keeps receiving events. Even the slowest allowed
# rate (1 event/min) writes at least every ~80 s, so 120 s without writes
# means the simulator is stuck.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,sys,time; sys.exit(0 if time.time()-os.path.getmtime(os.environ['OUTPUT_FILE'])<120 else 1)"

CMD ["python", "simulate_attacks.py"]