"""HTTP endpoints for the Beaver chat app. Mounted by main.py."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import engine
import planner
import policy

router = APIRouter(prefix="/api")


def _user_with_role(user_id: str, role: str) -> dict:
    """Server-side guard: the active role must be one the user actually holds.
    NOTE: prototype only. There is no login; production needs real authentication (the client says who it is)."""
    user = policy.get_user(user_id)
    if not user:
        raise HTTPException(404, "Unknown user")
    if role not in user["roles"] or policy.role_tags(role) is None:
        raise HTTPException(403, f"{user['name']} does not hold the '{role}' role")
    return user


def _require_admin(actor_id: str, actor_role: str):
    _user_with_role(actor_id, actor_role)
    if "*" not in (policy.role_tags(actor_role) or set()):
        raise HTTPException(403, "Only an admin role can manage users and roles")


class ChatIn(BaseModel):
    user_id: str
    role: str
    message: str


class AssignIn(BaseModel):
    actor_id: str
    actor_role: str
    roles: List[str]


class RoleIn(BaseModel):
    actor_id: str
    actor_role: str
    name: str
    description: str = ""
    allowed_tags: List[str]


@router.get("/health")
def health():
    return {"ollama": planner.ollama_status()}


@router.get("/users")
def users():
    return policy.load()["users"]


@router.get("/roles")
def roles():
    return policy.load()["roles"]


@router.get("/suggestions")
def suggestions(user_id: str, role: str):
    _user_with_role(user_id, role)
    return {"suggestions": engine.suggestions(role)}


@router.post("/chat")
def chat(body: ChatIn):
    user = _user_with_role(body.user_id, body.role)
    msg = body.message.strip()
    if not msg:
        raise HTTPException(400, "Empty message")
    try:
        return engine.ask(msg, user, body.role)
    except Exception as exc:  # keep the chat alive; surface a readable error
        return {"kind": "error", "role": body.role, "answer": f"Something went wrong while answering: {exc}"}


@router.put("/users/{user_id}/roles")
def assign_roles(user_id: str, body: AssignIn):
    _require_admin(body.actor_id, body.actor_role)
    data = policy.load()
    unknown = [r for r in body.roles if r not in data["roles"]]
    if unknown:
        raise HTTPException(400, f"Unknown roles: {unknown}")
    if not body.roles:
        raise HTTPException(400, "A user needs at least one role")
    user = next((u for u in data["users"] if u["id"] == user_id), None)
    if not user:
        raise HTTPException(404, "Unknown user")
    user["roles"] = body.roles
    policy.save(data)
    return user


@router.post("/roles")
def create_role(body: RoleIn):
    _require_admin(body.actor_id, body.actor_role)
    name = body.name.strip().lower().replace(" ", "_")
    data = policy.load()
    if not name or name in data["roles"]:
        raise HTTPException(400, "Role name is empty or already exists")
    data["roles"][name] = {"description": body.description, "allowed_tags": body.allowed_tags}
    policy.save(data)
    return {name: data["roles"][name]}
