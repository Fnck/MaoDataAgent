FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY --from=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml .
RUN uv sync --no-dev
COPY app ./app
COPY conf.yml ./conf.yml
COPY skills ./skills
COPY data ./data
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
EXPOSE 8010
ENTRYPOINT ["./entrypoint.sh"]
