# syntax=docker/dockerfile:1
ARG NODE_MAJOR=24
ARG DOTNET_IMAGE=mcr.microsoft.com/dotnet/sdk:10.0-noble
FROM node:${NODE_MAJOR}-bookworm-slim AS node
FROM ${DOTNET_IMAGE}

USER root
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=node /usr/local/ /usr/local/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash build-essential ca-certificates curl git jq libatomic1 mc \
        openssh-client python3 python3-dev python3-pip python3-venv \
        ripgrep tree \
    && install -d -m 0755 /etc/apt/keyrings \
    && curl --fail --show-error --location \
        https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        --output /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod 0644 /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && printf '%s\n' \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get clean \
    && find /var/lib/apt/lists -type f -delete

ARG PI_VERSION=1.6.0
RUN npm install --global --ignore-scripts "@earendil-works/pi-coding-agent@${PI_VERSION}" \
    && npm cache clean --force \
    && node --version \
    && pi --version

RUN useradd --create-home --uid 10001 --shell /bin/bash dev \
    && install -d -o dev -g dev /workspace \
        /home/dev/.pi /home/dev/.pi/agent \
        /home/dev/.nuget /home/dev/.nuget/packages

RUN dotnet tool install --tool-path /opt/dotnet-tools csharp-ls --version 0.28.0 \
    && dotnet tool install --tool-path /opt/dotnet-tools dotnet-ef --version '10.*' \
    && dotnet tool install --tool-path /opt/dotnet-tools csharpier \
    && dotnet tool install --tool-path /opt/dotnet-tools dotnet-outdated-tool

COPY --chmod=0755 entrypoint.sh /opt/pi/entrypoint.sh
COPY configure.py /opt/pi/configure.py
RUN sed -i 's/\r$//' /opt/pi/entrypoint.sh

ENV HOME=/home/dev \
    PATH=/opt/dotnet-tools:${PATH} \
    PI_CODING_AGENT_DIR=/home/dev/.pi/agent \
    PI_SKIP_VERSION_CHECK=1 \
    DOTNET_CLI_HOME=/home/dev \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_USE_POLLING_FILE_WATCHER=true \
    NUGET_PACKAGES=/home/dev/.nuget/packages \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8

USER dev
WORKDIR /workspace
RUN pwsh -NoLogo -NoProfile -NonInteractive -Command '$PSVersionTable.PSVersion.ToString()'
ENTRYPOINT ["/opt/pi/entrypoint.sh"]
CMD ["sleep", "infinity"]
