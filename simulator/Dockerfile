FROM python:3.12-slim

# Non-root user. The log directory is created and owned by this user in the
# image, so a fresh named volume mounted on it inherits that ownership.
RUN useradd --system --uid 10001 --no-create-home simulator \
    && mkdir -p /var/log/honeypot \
    && chown simulator:simulator /var/log/honeypot

WORKDIR /app
COPY simulator.py .

USER simulator
ENV PYTHONUNBUFFERED=1 \
    SIM_MODE=basic \
    SIM_OUTPUT=/var/log/honeypot/cowrie.json

# Healthy while the log file keeps receiving events (basic mode writes one
# every ~6 s, so 120 s without writes means the simulator is stuck).
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,sys,time; sys.exit(0 if time.time()-os.path.getmtime(os.environ['SIM_OUTPUT'])<120 else 1)"

CMD ["python", "simulator.py"]