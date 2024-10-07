# LLM Analytics
Super easy and effective llm analytics tool

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