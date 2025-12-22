from app.models.dynamodb import add_to_dynamodb
from app.utils.util import logger
import os

# Use environment variable, fallback to default
prompt_table = os.getenv("PROMPTS_TABLE_NAME")

class Prompts:
    def __init__(self, payload: dict):
        self.prompt_PK = payload.get("prompt_PK")
        self.session_PK = payload.get("session_PK")
        self.chat_PK = payload.get("chat_PK")
        self.user_PK = payload.get("user_PK")
        self.promptText = payload.get("promptText")
        self.promptsStatus = payload.get("promptsStatus")
        self.response = payload.get("response", {})
        self.guardrails = payload.get("guardrails")
        self.feedback = payload.get("feedback")
        self.auditCreateDateTime = payload.get("auditCreateDateTime")
        self.auditLastUpdateDateTime = payload.get("auditLastUpdateDateTime")
        self.gateway_response_time = payload.get("gateway_response_time")

        # Basic validation
        required_fields = [
            self.prompt_PK,
            self.session_PK,
            self.chat_PK,
            self.user_PK,
            self.promptText,
            self.promptsStatus,
            self.response,
            self.auditCreateDateTime
        ]
        if any(field is None for field in required_fields):
            raise ValueError("Missing required fields in prompt payload")

    def to_dict(self):
        return {
            "prompt_PK": self.prompt_PK,
            "session_PK": self.session_PK,
            "chat_PK": self.chat_PK,
            "user_PK": self.user_PK,
            "promptText": self.promptText,
            "promptsStatus": self.promptsStatus,
            "response": self.response,
            "guardrails": self.guardrails,
            "feedback": self.feedback,
            "auditCreateDateTime": self.auditCreateDateTime,
            "auditLastUpdateDateTime": self.auditLastUpdateDateTime,
            "gateway_response_time": self.gateway_response_time,
        }

def add_prompt(payload: dict, lambda_name: str):
    prompt = Prompts(payload)
    prompt_dict = prompt.to_dict()
    logger.info(f"Prompt payload being written: {prompt_dict}")
    return add_to_dynamodb(prompt_table, prompt_dict, lambda_name)
