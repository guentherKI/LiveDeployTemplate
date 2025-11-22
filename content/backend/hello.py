from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/hello")
def hello():
    return {"message": "hello "}
