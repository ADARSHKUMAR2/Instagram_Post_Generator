from pydantic import BaseModel, Field

class PostRequest(BaseModel):
    category_request: str = Field(
        ..., 
        description="The user's prompt, e.g., 'Create a weather post for Meerut today.'"
    )

class PostResponse(BaseModel):
    status: str
    content: str