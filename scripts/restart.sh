docker rm -f llm-analytics
docker build . -t llm-analytics
docker run --name llm-analytics -p 5000:5000 --env-file aws/env.list llm-analytics
