# kdb-q-challenges benchmark runner
# Sandboxed execution for evaluating LLM-generated q code safely.
#
# Prerequisites:
#   - Place your kc.lic license file in this directory before building
#
# Build:
#   docker build -t kdb-q-challenges .
#
# Run:
#   docker run --rm \
#     -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
#     -e OPENAI_API_KEY=$OPENAI_API_KEY \
#     -v $(pwd)/results:/app/results \
#     kdb-q-challenges \
#     --models claude-sonnet-4-6 --challenges all --attempts 3

FROM python:3.11-slim

# Install kdb+ personal edition
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates unzip \
    && rm -rf /var/lib/apt/lists/*

# Download kdb+ (user must supply license separately)
# The personal edition download URL changes; adjust as needed.
# Alternatively, mount /opt/q from the host.
RUN mkdir -p /opt/q
ENV QHOME=/opt/q
ENV PATH="$PATH:/opt/q/l64"

# Copy license if provided at build time
COPY kc.lic* /opt/q/

WORKDIR /app

# Install Python dependencies
COPY runner/requirements.txt runner/requirements.txt
RUN pip install --no-cache-dir -r runner/requirements.txt

# Copy project
COPY . .

# Default: run the benchmark
ENTRYPOINT ["python", "-m", "runner.runner"]
CMD ["--models", "claude-sonnet-4-6", "--challenges", "all"]
