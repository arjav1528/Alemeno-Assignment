from fastapi import FastAPI

from sqlalchemy.ext.declarative import declarative_base
from db.database import engine
from routers.jobs import router as jobs_router


app = FastAPI()

Base = declarative_base()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(jobs_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}
