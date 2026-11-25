from app.schemas.auth import CompanyRegister

from app.services.auth.company_registration import (
    register_company as register_company_service,
    OrganizationEmailAlreadyRegisteredError,
)

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db, settings
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    EmailVerificationRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.auth.registration import (
    register_user,
    EmailAlreadyRegisteredError,
)
from app.services.auth.login import (
    authenticate_user,
    InvalidCredentialsError,
    InactiveAccountError,
    EmailNotVerifiedError,
)
from app.services.auth.refresh import (
    create_refresh_token,
    rotate_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    InvalidRefreshTokenError,
)
from app.services.auth.email_verification import (
    verify_email,
    resend_verification_token,
    InvalidVerificationTokenError,
    VerificationResendCooldownError,
)
from app.services.auth.password_reset import (
    create_password_reset_token,
    reset_user_password,
    InvalidPasswordResetTokenError,
)
from app.services.email import (
    send_verification_email,
    send_password_reset_email,
    EmailDeliveryError,
)


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    try:
        user, verification_token = register_user(
            db,
            user_data,
        )

        try:
            send_verification_email(
                recipient=user.email,
                recipient_name=user.email.split("@")[0],
                verification_token=verification_token,
            )
        except EmailDeliveryError:
            logger.error(
                "Verification email delivery failed for user_id=%s",
                user.id,
            )

        return user

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )



@router.post(
    "/register/company",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_company_endpoint(
    company_data: CompanyRegister,
    db: Session = Depends(get_db),
):
    try:
        user, _, verification_token = register_company_service(
            db,
            company_data,
        )

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this administrator email already exists.",
        )

    except OrganizationEmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This company email is already registered.",
        )

    try:
        send_verification_email(
            recipient=user.email,
            recipient_name=user.email.split("@")[0],
            verification_token=verification_token,
        )
    except EmailDeliveryError:
        logger.exception(
            "Company administrator verification email delivery failed "
            "for user_id=%s",
            user.id,
        )

    return user



@router.post(
    "/verify-email",
    response_model=UserResponse,
)
def verify_user_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    try:
        user = verify_email(
            db,
            verification_data.token,
        )

        return user

    except InvalidVerificationTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
)
def resend_user_verification(
    request_data: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    try:
        verification_token = resend_verification_token(
            db,
            request_data.email,
        )

        if verification_token is not None:
            try:
                send_verification_email(
                    recipient=request_data.email.lower(),
                    recipient_name=request_data.email.split("@")[0],
                    verification_token=verification_token,
                )
            except EmailDeliveryError:
                logger.error(
                    "Verification email delivery failed during resend."
                )

    except VerificationResendCooldownError:
        pass

    return {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
)
def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    email = str(request_data.email).lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is not None and user.is_active:
        try:
            reset_token = create_password_reset_token(
                db,
                user.id,
            )

            db.commit()

            try:
                send_password_reset_email(
                    recipient=user.email,
                    recipient_name=user.email.split("@")[0],
                    reset_token=reset_token,
                )
            except EmailDeliveryError:
                logger.error(
                    "Password reset email delivery failed "
                    "for user_id=%s",
                    user.id,
                )

        except Exception:
            db.rollback()
            logger.exception(
                "Password reset request failed for user_id=%s",
                user.id,
            )

    return {
        "message": (
            "If an account exists with that email, "
            "password reset instructions will be sent."
        )
    }


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
)
def reset_password(
    request_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        reset_user_password(
            db,
            raw_token=request_data.token,
            new_password=request_data.new_password,
        )

        return {
            "message": "Your password has been reset successfully."
        }

    except InvalidPasswordResetTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or expired.",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        user, access_token = authenticate_user(
            db,
            login_data,
        )

        refresh_token = create_refresh_token(
            db,
            user.id,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/api/v1/auth",
        )

        return TokenResponse(
            access_token=access_token,
        )

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except InactiveAccountError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    
    except EmailNotVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in.",
        )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user



@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = request.cookies.get("refresh_token")

    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing or invalid.",
        )

    try:
        new_access_token, new_refresh_token = rotate_refresh_token(
            db,
            raw_refresh_token,
        )

    except InvalidRefreshTokenError:
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing or invalid.",
        )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=new_access_token,
    )

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = request.cookies.get("refresh_token")

    if raw_refresh_token:
        token_record = validate_refresh_token(
            db,
            raw_refresh_token,
        )

        if token_record is not None:
            revoke_refresh_token(db, token_record)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )

    response.status_code = status.HTTP_204_NO_CONTENT

    return response