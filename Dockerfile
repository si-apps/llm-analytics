FROM python:3.12-alpine
ARG APP_VERSION
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /app
ENV FLASK_APP=app.py
COPY src/*.py .
COPY src/templates/* ./templates/
COPY src/static/* ./static/
COPY src/logging.conf .
CMD [ "python", "-u", "./app.py", "$APP_VERSION"]
