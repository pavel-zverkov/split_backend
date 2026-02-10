from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user
from .user_model import User
from .claim_request_model import ClaimRequest as ClaimRequestModel
from .claim_request_schema import (
    ClaimRequest,
    ClaimRequestResponse,
    ClaimRequestItem,
    MyClaimRequestsResponse,
    ClaimRequestDetailItem,
    UserBriefForClaim,
    PendingClaimsResponse,
    PendingClaimItem,
    ClaimerBrief,
    ClaimStatusUpdate,
)
from ..enums.claim_status import ClaimStatus
from ..enums.account_type import AccountType

claim_request_router = APIRouter(tags=['claim-requests'])


@claim_request_router.post(
    '/api/users/me/claim',
    response_model=ClaimRequestResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def claim_ghost_users(
    request: ClaimRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    claim_requests = []

    for ghost_id in request.ghost_user_ids:
        # Verify ghost user exists
        ghost_user = db.query(User).filter(
            User.id == ghost_id,
            User.account_type == AccountType.GHOST,
            User.is_active == True
        ).first()

        if not ghost_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Ghost user {ghost_id} not found'
            )

        # Check if claim already exists
        existing_claim = db.query(ClaimRequestModel).filter(
            ClaimRequestModel.claimer_id == current_user.id,
            ClaimRequestModel.ghost_user_id == ghost_id,
            ClaimRequestModel.status == ClaimStatus.PENDING
        ).first()

        if existing_claim:
            claim_requests.append(ClaimRequestItem(
                id=existing_claim.id,
                ghost_user_id=existing_claim.ghost_user_id,
                status=existing_claim.status,
                approver_id=existing_claim.approver_id,
            ))
            continue

        # Create claim request
        claim = ClaimRequestModel(
            claimer_id=current_user.id,
            ghost_user_id=ghost_id,
            approver_id=ghost_user.created_by,
            status=ClaimStatus.PENDING,
        )

        db.add(claim)
        db.commit()
        db.refresh(claim)

        claim_requests.append(ClaimRequestItem(
            id=claim.id,
            ghost_user_id=claim.ghost_user_id,
            status=claim.status,
            approver_id=claim.approver_id,
        ))

    return ClaimRequestResponse(claim_requests=claim_requests)


@claim_request_router.get(
    '/api/users/me/claim-requests',
    response_model=MyClaimRequestsResponse
)
async def get_my_claim_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    claims = db.query(ClaimRequestModel).filter(
        ClaimRequestModel.claimer_id == current_user.id
    ).all()

    result = []
    for claim in claims:
        ghost_user = db.query(User).filter(User.id == claim.ghost_user_id).first()
        result.append(ClaimRequestDetailItem(
            id=claim.id,
            ghost_user=UserBriefForClaim(
                id=ghost_user.id,
                username_display=ghost_user.username_display,
            ) if ghost_user else None,
            status=claim.status,
            created_at=claim.created_at,
        ))

    return MyClaimRequestsResponse(claims=result)


@claim_request_router.get(
    '/api/claim-requests/pending',
    response_model=PendingClaimsResponse
)
async def get_pending_claims_to_approve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    claims = db.query(ClaimRequestModel).filter(
        ClaimRequestModel.approver_id == current_user.id,
        ClaimRequestModel.status == ClaimStatus.PENDING
    ).all()

    result = []
    for claim in claims:
        claimer = db.query(User).filter(User.id == claim.claimer_id).first()
        ghost_user = db.query(User).filter(User.id == claim.ghost_user_id).first()

        result.append(PendingClaimItem(
            id=claim.id,
            claimer=ClaimerBrief(
                id=claimer.id,
                username_display=claimer.username_display,
                first_name=claimer.first_name,
            ) if claimer else None,
            ghost_user=UserBriefForClaim(
                id=ghost_user.id,
                username_display=ghost_user.username_display,
            ) if ghost_user else None,
            created_at=claim.created_at,
        ))

    return PendingClaimsResponse(claims=result)


@claim_request_router.patch(
    '/api/claim-requests/{request_id}',
    status_code=status.HTTP_200_OK
)
async def update_claim_status(
    request_id: int,
    update: ClaimStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    claim = db.query(ClaimRequestModel).filter(
        ClaimRequestModel.id == request_id
    ).first()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Claim request not found'
        )

    # Only approver can update status
    if claim.approver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only the ghost user creator can approve/reject claims'
        )

    if claim.status != ClaimStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Claim request already processed'
        )

    if update.status not in [ClaimStatus.APPROVED, ClaimStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Status must be approved or rejected'
        )

    claim.status = update.status
    db.commit()

    # If approved, merge ghost user into claimer
    if update.status == ClaimStatus.APPROVED:
        _merge_ghost_into_user(db, claim.ghost_user_id, claim.claimer_id)

    return {'status': 'ok'}


def _merge_ghost_into_user(db: Session, ghost_user_id: int, claimer_id: int) -> None:
    from ..result.result_model import Result
    from ..competition.competition_registration_model import CompetitionRegistration
    from ..club.club_membership_model import ClubMembership
    from .user_qualification_model import UserQualification

    # Update Result.user_id
    db.query(Result).filter(Result.user_id == ghost_user_id).update(
        {'user_id': claimer_id}
    )

    # Update CompetitionRegistration.user_id
    db.query(CompetitionRegistration).filter(
        CompetitionRegistration.user_id == ghost_user_id
    ).update({'user_id': claimer_id})

    # Update ClubMembership.user_id
    db.query(ClubMembership).filter(
        ClubMembership.user_id == ghost_user_id
    ).update({'user_id': claimer_id})

    # Transfer UserQualification records
    db.query(UserQualification).filter(
        UserQualification.user_id == ghost_user_id
    ).update({'user_id': claimer_id})

    # Delete ghost user record
    ghost_user = db.query(User).filter(User.id == ghost_user_id).first()
    if ghost_user:
        db.delete(ghost_user)

    db.commit()
