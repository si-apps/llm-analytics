# LLM Analytics
Effective llm analytics tool

### Install
This command runs a Docker container using the image `si4apps/llm-analytics` and maps it to the local port `5000`.
```
docker rm -f llm-analytics
docker run --name llm-analytics -p 5000:5000 --env-file aws/env.list si4apps/llm-analytics
```
--env-file aws/env.list:
Specifies an environment file that contains key-value pairs (like API keys, credentials, or settings) to set up environment variables inside the container.
Example content of aws/env.list:
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SERET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
```
### Bedrock User Permissions 
Permissions needed:
```
{
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "arn:aws:bedrock:*::foundation-model/*"
        }
    ]
}
```