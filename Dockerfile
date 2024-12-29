FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ADD /src src
ADD /pyproject.toml pyproject.toml
ADD /uv.lock uv.lock
RUN uv sync --frozen --no-install-project --no-dev
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["uv"]
CMD ["run", "src/main.py"]
