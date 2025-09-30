FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD exec functions-framework --target=process_sudoku_screenshot --port=${PORT:-8080}