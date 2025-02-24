# LLM Analytics

Analyze Your Data Securely with AI. Choose your file and get instant insights through natural language questions - all processed locally and privately in your browser.

A limited preview of the LLM Analytics application can be found [here](https://freetextanalytics.com/).

### Features
- **Secure & Private**: All data stays in your browser. Nothing is sent to external servers.
- **Handle Large Files**: Process millions of records efficiently without size limits.
- **Natural Conversations**: Ask follow-up questions and dive deeper into your data.

### Installation

Prerequisites:
1. To install the LLM Analytics you need to have Docker installed. If you don't have it installed you can download it from [here](https://www.docker.com/products/docker-desktop).
2. You need to configure the model LLM Analytics will use and configure your env.list configuration file. See the [Configuration](#configuration) section for more details.

This command runs a Docker container using the image `si4apps/llm-analytics` and maps it to the local port `5000`.
```bash
docker run -d --name llm-analytics -p 5000:5000 --env-file env.list si4apps/llm-analytics
```
If an existing container exists you should remove it first using the following command:
```bash
docker rm -f llm-analytics
```
### Configuration
The installation command parameter --env-file env.list specifies an environment file that contains key-value pairs (like API keys, credentials, or settings) to set up environment variables inside the container. 

#### Google Gemini
Example content of env.list:
```
GENIMI_API_KEY=your-api-key
MODEL_ID=gemini-2.0-flash
```

#### AWS Bedrock 
Example content of env.list:
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SERET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
MODEL_ID=anthropic.claude-instant-v1
```


The following policy is an example of the permissions needed for the Bedrock service. You can attach this policy to the user you are using to access the Bedrock service.
```json
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
