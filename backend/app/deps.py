from typing import Optional

from fastapi import Header, HTTPException


def acting_member_id(x_member_id: Optional[int] = Header(default=None)) -> int:
    if x_member_id is None:
        raise HTTPException(status_code=400, detail="X-Member-Id header is required")
    return x_member_id
