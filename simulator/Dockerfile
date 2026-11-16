FROM python:3.12-alpine

# Non-root user. Alpine has no useradd, so the user is created with the
# busybox commands. The log directory is created and owned by this user in
# the image, so a fresh named volume mounted on it inherits that ownership.
RUN addgroup -S -g 10001 simulator \
    && adduser -S -D -H -u 10001 -G simulator simulator \
    && mkdir -p /var/log/honeypot \
    && chown simulator:simulator /var/log/honeypot

# The script stays owned by root: the simulator user can run it but not
# modify it.
WORKDIR /app
COPY simulate_attacks.py .

# Numeric uid:gid, so the runtime can check that the user is not root without
# reading /etc/passwd.
USER 10001:10001
# PYTHONDONTWRITEBYTECODE: the root filesystem is read-only in Compose, so
# Python must not try to write .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SIMULATOR_MODE=basic \
    OUTPUT_FILE=/var/log/honeypot/cowrie.json

# Healthy while the log file keeps receiving events. The simulator writes one
# event per interval, and the longest pause is 78 s (60 s x 1.3 at the minimum
# rate of 1 event/min), so 120 s without writes means it is stuck.
# Exec form: Docker runs Python directly, without a /bin/sh in between.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,sys,time; sys.exit(0 if time.time()-os.path.getmtime(os.environ['OUTPUT_FILE'])<120 else 1)"]

# Exec form: Python is PID 1 and receives SIGTERM directly, so the simulator
# closes the log file cleanly on docker stop. Extra arguments given at run
# time (for example --mode stress) are passed to the script.
ENTRYPOINT ["python", "simulate_attacks.py"]
