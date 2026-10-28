import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _check_date(v: str) -> str:
    import datetime as dt
    if not DATE_RE.match(v):
        raise ValueError("date must be YYYY-MM-DD")
    dt.date.fromisoformat(v)
    return v


class ExpenseIn(BaseModel):
    amount: float = Field(gt=0)
    category: str
    spent_on: str
    note: str = ""

    _d = field_validator("spent_on")(_check_date)


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    spent_on: Optional[str] = None
    note: Optional[str] = None

    @field_validator("spent_on")
    @classmethod
    def _d(cls, v):
        return v if v is None else _check_date(v)


class Expense(BaseModel):
    expense_id: int
    amount: float
    category: str
    spent_on: str
    note: Optional[str]
    updated_at: str
    synced: bool


class ExpensePage(BaseModel):
    items: list[Expense]
    total: int


class BudgetIn(BaseModel):
    category: str
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    limit_amt: float = Field(gt=0)
