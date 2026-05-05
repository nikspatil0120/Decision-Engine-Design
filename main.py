from fastapi import FastAPI
from routes.decision import router as decision_router

app = FastAPI(
    title="AI Voice Interview — Decision Engine",
    description="Rule-based decision engine for difficulty adjustment and session control.",
    version="1.0.0",
)

app.include_router(decision_router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "decision-engine"}
