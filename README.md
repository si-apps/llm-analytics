# LLM Analytics

Analyze Your Data Securely with AI. Choose your file and get instant insights through natural language questions - all processed locally and privately in your browser.

A limited preview of the LLM Analytics application can be found [here](https://freetextanalytics.com/).

### Features
- **Secure & Private**: All data stays in your browser. Nothing is sent to external servers.
- **Handle Large Files**: Process millions of records efficiently without size limits.
- **Natural Conversations**: Ask follow-up questions and dive deeper into your data.

### Installation

Prerequisites:
1. To install the LLM Analytics you need to have a Docker installed on your machine. If you don't have it installed you can download it from [here](https://www.docker.com/products/docker-desktop).
2. You need to have an AWS account to use the Bedrock service. If you don't have an account you can create one [here](https://aws.amazon.com/). See below for the permissions needed for the Bedrock service.

This command runs a Docker container using the image `si4apps/llm-analytics` and maps it to the local port `5000`.
```
docker run -d --name llm-analytics -p 5000:5000 --env-file env.list si4apps/llm-analytics
```
If an existing container exists you should remove it first using the following command:
```
docker rm -f llm-analytics
```
--env-file env.list:
Specifies an environment file that contains key-value pairs (like API keys, credentials, or settings) to set up environment variables inside the container.
Example content of aws/env.list:
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SERET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
```
### Bedrock User Permissions 

The following policy is an example of the permissions needed for the Bedrock service. You can attach this policy to the user you are using to access the Bedrock service.
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