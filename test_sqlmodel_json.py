from sqlmodel import SQLModel, Field, JSON
from typing import Optional, List, Dict, Any

class TestModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    requirements: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON)

print("Model created successfully")
