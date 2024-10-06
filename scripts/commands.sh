python3.12 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt --upgrade && pip install -r test/test.requirements.txt --upgrade

zip llm-analytics.zip requirements.txt Dockerfile commands.sh src/*.py src/logging.conf src/templates/index.html src/static/style.css

unzip llm-analytics.zip
docker rm -f llm-analytics
docker build . -t llm-analytics
docker run --name llm-analytics -d -p 5000:5000 --env-file aws/env.list llm-analytics
