import uuid

from app.core.security import (
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.models.user import User
from app.repositories.user_repository import UserRepository


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, email: str, password: str, full_name: str) -> User:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise AuthError("An account with this email already exists")

        user = await self.user_repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await self.user_repo.commit()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("This account has been deactivated")
        return user

    @staticmethod
    def issue_tokens(user: User) -> tuple[str, str]:
        access_token = create_token(str(user.id), "access")
        refresh_token = create_token(str(user.id), "refresh")
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except InvalidTokenError as exc:
            raise AuthError("Invalid or expired refresh token") from exc

        user = await self.user_repo.get(uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise AuthError("User not found or inactive")

        return self.issue_tokens(user)
