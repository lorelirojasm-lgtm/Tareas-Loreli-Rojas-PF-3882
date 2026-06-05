FROM python:3.11-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p pacts

CMD ["pytest", "tests/pact", "-v", "--tb=short"]
