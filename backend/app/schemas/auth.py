from pydantic import BaseModel
class LoginRequest(BaseModel):
    email: str
    password: str
class TokenResponse(BaseModel):
    token: str
    role: str
class User(BaseModel):
    id: str
    name: str
    email: str
    role: str
