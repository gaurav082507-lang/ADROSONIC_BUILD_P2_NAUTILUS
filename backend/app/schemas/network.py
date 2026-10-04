from pydantic import BaseModel

class Node(BaseModel):
    id: str
    label: str
    kind: str

class Edge(BaseModel):
    source: str
    target: str
    reason: str
