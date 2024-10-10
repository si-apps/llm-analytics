FROM python:3.12-alpine
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /app
ENV FLASK_APP=app.py
COPY src/*.py .
COPY src/templates/index.html ./templates/
COPY src/static/* ./static/
COPY src/logging.conf .
CMD [ "python", "-u", "./app.py"]
