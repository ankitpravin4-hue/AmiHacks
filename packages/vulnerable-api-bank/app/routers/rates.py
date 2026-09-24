"""Public FX rates — intentionally safe."""

from fastapi import APIRouter

from app.schemas import RateOut

router = APIRouter(tags=["rates"])


@router.get("/rates", response_model=list[RateOut])
def list_rates() -> list[RateOut]:
    """Return public currency quotes. No auth, no sensitive fields."""
    return [
        RateOut(pair="USD/EUR", rate=0.92),
        RateOut(pair="USD/GBP", rate=0.79),
        RateOut(pair="USD/INR", rate=83.4),
    ]
