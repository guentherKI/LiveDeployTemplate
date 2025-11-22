from fastapi import APIRouter
const port = process.env.PORT || 10000

router = APIRouter(prefix="/api")

@router.get("/hello")
def hello():
    return {"message": "hello "}
