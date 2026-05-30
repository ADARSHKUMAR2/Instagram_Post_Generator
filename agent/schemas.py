from pydantic import BaseModel, Field

class PostRequest(BaseModel):
    prompt: str = Field(
        ..., 
        description="The user's prompt, e.g., 'Create a weather post for Meerut today.'"
    )

class InstaPost(BaseModel):
    caption: str
    image_prompt: str

class PostResponse(BaseModel):     
    status: str
    content: InstaPost
    image_url: str | None = None
