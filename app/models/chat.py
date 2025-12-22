from app.models.dynamodb import add_to_dynamodb, dynamoDb
from app.utils.util import logger
from boto3.dynamodb.conditions import Key
import os

# Use environment variable, fallback to default
chat_table_name = os.getenv("CHATS_TABLE_NAME")
table = dynamoDb.Table(chat_table_name)

class Chat:
    def __init__(self, payload: dict):
        self.chat_PK = payload.get("chat_PK")
        self.session_PK = payload.get("session_PK")
        self.user_PK = payload.get("user_PK")
        self.document_PK = payload.get("document_PK", [])
        self.promptTemplate_PK = payload.get("promptTemplate_PK")
        self.prompt_PK = payload.get("prompt_PK", [])
        self.title = payload.get("title")
        self.summary = payload.get("summary")
        self.auditCreateDateTime = payload.get("auditCreateDateTime")
        self.auditLastUpdateDateTime = payload.get("auditLastUpdateDateTime")
        self.genai_feature = payload.get("genai_feature")

        # Basic validation
        if not all([self.chat_PK, self.session_PK, self.user_PK, self.auditCreateDateTime]):
            raise ValueError("Missing required fields in Chat payload")

    def to_dict(self):
        return {
            "chat_PK": self.chat_PK,
            "session_PK": self.session_PK,
            "user_PK": self.user_PK,
            "document_PK": self.document_PK,
            "promptTemplate_PK": self.promptTemplate_PK,
            "prompt_PK": self.prompt_PK,
            "title": self.title,
            "summary": self.summary,
            "auditCreateDateTime": self.auditCreateDateTime,
            "auditLastUpdateDateTime": self.auditLastUpdateDateTime,
            "genai_feature": self.genai_feature
        }

def add_chat(payload: dict, lambda_name: str):
    chat = Chat(payload)
    chat_dict = chat.to_dict()
    print(f"Chat payload being written: {chat_dict}")  # Debugging
    logger.info(f"Chat payload being written: {chat_dict}")

    existing = table.get_item(Key={"chat_PK": chat.chat_PK})

    if "Item" in existing:
        # Update the existing record's session_PK and audit fields
        response = table.update_item(
            Key={"chat_PK": chat.chat_PK},
            UpdateExpression="""
                SET session_PK = :s,
                    auditLastUpdateDateTime = :u,
                    title = :t,
                    summary = :sum,
                    document_PK = :d,
                    prompt_PK = :p,
                    promptTemplate_PK = :pt,
                    genai_feature = :g,
                    user_PK = :user
            """,
            ExpressionAttributeValues={
                ":s": chat.session_PK,
                ":u": chat.auditLastUpdateDateTime,
                ":t": chat.title,
                ":sum": chat.summary,
                ":d": chat.document_PK,
                ":p": chat.prompt_PK,
                ":pt": chat.promptTemplate_PK,
                ":g": chat.genai_feature,
                ":user": chat.user_PK
            },
            ReturnValues="ALL_NEW"
        )
        updated_item = response.get("Attributes", {})
        logger.info(f"Updated chat {chat.chat_PK} with new session_PK {chat.session_PK}")
        logger.debug(f"Updated item: {updated_item}")
        return updated_item
    else:
        logger.info(f"No existing chat found. Creating new chat {chat.chat_PK}")
        return add_to_dynamodb(chat_table_name, chat_dict, lambda_name)
