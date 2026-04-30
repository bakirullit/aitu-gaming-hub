from fastapi import FastAPI

app = FastAPI(title="AITU Gaming Platform")

@app.get("/")
async def root():
    return {"status": "alive"}