from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class UserIntent(BaseModel):
    intent: Literal["value_prop", "recommend", "finance", "other"] = Field(
        description="User intent: value_prop (questions about Kavak), recommend (car recommendations), finance (financing questions), other"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for intent classification"
    )


class CarPreferences(BaseModel):
    brand: Optional[str] = Field(None, description="Car brand (normalized)")
    model: Optional[str] = Field(None, description="Car model (normalized)")
    budget_max: Optional[int] = Field(None, ge=0, description="Maximum budget in MXN")
    year_min: Optional[int] = Field(None, ge=1900, le=2030, description="Minimum year")
    year_max: Optional[int] = Field(None, ge=1900, le=2030, description="Maximum year")
    transmission: Optional[Literal["automatic", "manual"]] = Field(
        None, description="Transmission type"
    )
    fuel: Optional[Literal["gasoline", "diesel", "hybrid", "electric"]] = Field(
        None, description="Fuel type"
    )
    city: Optional[str] = Field(None, description="City/location preference")
    mileage_max: Optional[int] = Field(None, ge=0, description="Maximum mileage in km")


class FinancingPlan(BaseModel):
    monthly_payment: float = Field(description="Monthly payment amount in MXN")
    total_interest: float = Field(description="Total interest paid in MXN")
    total_amount: float = Field(description="Total amount paid (principal + interest)")
    principal: float = Field(description="Principal amount (price - down_payment)")
    interest_rate: float = Field(
        description="Annual interest rate (e.g., 0.10 for 10%)"
    )
    term_years: int = Field(description="Financing term in years")
    term_months: int = Field(description="Financing term in months")


class Car(BaseModel):
    id: str = Field(description="Car ID (stock_id)")
    brand: str = Field(description="Car brand (make)")
    model: str = Field(description="Car model")
    year: int = Field(description="Car year")
    price: float = Field(description="Car price in MXN")
    mileage: int = Field(description="Mileage in km")
    version: Optional[str] = Field(None, description="Car version/trim")
    bluetooth: Optional[bool] = Field(None, description="Has Bluetooth")
    car_play: Optional[bool] = Field(None, description="Has Apple CarPlay")
    length: Optional[float] = Field(None, description="Car length in mm (largo)")
    width: Optional[float] = Field(None, description="Car width in mm (ancho)")
    height: Optional[float] = Field(None, description="Car height in mm (altura)")
    transmission: Optional[str] = Field(None, description="Transmission type")
    fuel: Optional[str] = Field(None, description="Fuel type")
    city: Optional[str] = Field(None, description="City/location")
    url: Optional[str] = Field(None, description="Car URL")


class RAGAnswer(BaseModel):
    answer: str = Field(description="Answer text")
    sources: List[str] = Field(default_factory=list, description="Source citations")


class BotReply(BaseModel):
    message: str = Field(description="Response message to user")
    recommended_car_ids: List[str] = Field(
        default_factory=list,
        description="IDs of recommended cars (must exist in catalog)",
    )
    financing: Optional[FinancingPlan] = Field(
        None, description="Financing plan if applicable"
    )
    citations: List[str] = Field(
        default_factory=list, description="Citations for value prop answers"
    )


class UserState(BaseModel):
    user_id: str = Field(description="User ID")
    name: Optional[str] = Field(None, description="User name")
    city: Optional[str] = Field(None, description="User city")
    intent_stage: Literal["exploring", "comparing", "financing_ready"] = Field(
        default="exploring", description="Current intent stage"
    )
    preferences: Optional[CarPreferences] = Field(None, description="User preferences")
    last_results: List[str] = Field(
        default_factory=list, description="IDs of last recommended cars"
    )
    financing_context: Optional[dict] = Field(
        None, description="Financing context (price, down_payment, term, rate)"
    )
