from typing import List, Any
from pydantic import BaseModel

class CanonicalResponse(BaseModel):

    api_version = "1.0"
    value: Any = None
    errors: Any = None

CanonicalResponse_Ok = CanonicalResponse(value="ok")
