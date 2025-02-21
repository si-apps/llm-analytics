docker rm -f llm-analytics
docker run --name si4apps/llm-analytics -p 5000:5000 --env-file aws/env.list llm-analytics
