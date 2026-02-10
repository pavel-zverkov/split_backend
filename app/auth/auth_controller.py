from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..user.user_model import User
from ..enums.account_type import AccountType
from .auth_schema import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    AuthResponse,
    RefreshTokenRequest,
    TokenResponse,
    LogoutRequest,
    UserBrief,
    TokenPayload,
)
from .auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)

auth_router = APIRouter(prefix='/api/auth', tags=['auth'])


@auth_router.post('/register', response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Check username uniqueness
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username already registered'
        )

    # Check email uniqueness if provided
    if request.email:
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Email already registered'
            )

    # Create user
    user = User(
        username=request.username,
        username_display=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        account_type=AccountType.REGISTERED,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate tokens
    token_data = TokenPayload.from_user(user).model_dump(mode='json')
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return RegisterResponse(
        user=UserBrief(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            account_type=user.account_type,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
        suggested_ghosts=[],
    )


@auth_router.post('/login', response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == request.login) | (User.email == request.login)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )

    # Check if ghost user
    if user.account_type == AccountType.GHOST:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )

    # Verify password
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )

    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is deactivated'
        )

    # Generate tokens
    token_data = TokenPayload.from_user(user).model_dump(mode='json')
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return AuthResponse(
        user=UserBrief(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            account_type=user.account_type,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@auth_router.post('/refresh', response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token'
        )

    if payload.get('type') != 'refresh':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token type'
        )

    user_id = payload.get('user_id')
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token'
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or inactive'
        )

    # Generate new tokens
    token_data = TokenPayload.from_user(user).model_dump(mode='json')
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@auth_router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user)
):
    # In a production system, we would add the refresh token to a blacklist
    # For now, the client simply discards the tokens
    return None
