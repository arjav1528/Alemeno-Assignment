from fastapi import FastAPI

from db.database import Base, engine
from routers.jobs import router as jobs_router
from routers.transaction import router as transaction_router

app = FastAPI()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(jobs_router)
app.include_router(transaction_router)



@app.get("/")
async def root():
    return {"message": "Hello World"}
