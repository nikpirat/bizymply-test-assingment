from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from station_health.supplied import TOKENS

# auto_error=False so we control the response: a uniform 401 with a
# WWW-Authenticate header for both "missing" and "unknown" tokens.
_bearer = HTTPBearer(auto_error=False)


def get_operator_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> int:
    """Resolve the bearer token to the authenticated operator's id."""
    operator_id = TOKENS.get(credentials.credentials) if credentials else None
    if operator_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return operator_id


OperatorId = Annotated[int, Depends(get_operator_id)]
