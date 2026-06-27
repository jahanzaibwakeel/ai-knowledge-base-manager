from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import core_schema


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def validate(cls, value: str | ObjectId) -> str:
        if isinstance(value, ObjectId):
            return str(value)
        if ObjectId.is_valid(value):
            return str(value)
        raise ValueError("Invalid ObjectId")


class MongoModel(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, json_encoders={ObjectId: str})
