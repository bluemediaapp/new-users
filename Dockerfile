FROM python:3.9

WORKDIR opt/
RUN pip install poetry
COPY poetry.lock ./
COPY pyproject.toml ./
RUN poetry install

COPY . ./
CMD ["poetry", "run", "uvicorn", "main:app", "--port", "5000", "--host", "0.0.0.0"]
