import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(401, "Invalid token.")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token.")

    user = await User.filter(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(401, "User not found.")
    return user
