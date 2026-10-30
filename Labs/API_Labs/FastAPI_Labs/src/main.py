from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from predict import predict_data


app = FastAPI(title="Legendary or Mid?")

class PokemonStats(BaseModel):
    """
    Pydantic BaseModel representing a Pokemon's base stats.

    Attributes:
        hp (float): Hit points.
        attack (float): Physical attack.
        defense (float): Physical defense.
        sp_atk (float): Special attack.
        sp_def (float): Special defense.
        speed (float): Speed.
    """
    hp: float
    attack: float
    defense: float
    sp_atk: float
    sp_def: float
    speed: float

class VerdictResponse(BaseModel):
    response: str



"""Modern web apps use a technique named routing. This helps the user remember the URLs.
For instance, instead of having /booking.php they see /booking/. Instead of /account.asp?id=1234/
they’d see /account/1234/."""

@app.get("/", status_code=status.HTTP_200_OK)
async def health_ping():
    """Concurrent (multiple tasks can run simultaneously)"""
    return {"status": "healthy"}

@app.post("/predict", response_model=VerdictResponse)
async def predict_pokemon(stats: PokemonStats):
    """
    Judge whether a Pokemon is legendary or just mid based on its base stats.
    Args:
        stats (PokemonStats): A PokemonStats object containing hp, attack, defense,
            sp_atk, sp_def and speed.
    Returns:
        VerdictResponse: A response object containing:
            - response (str): "legendary" or "mid"
    Raises:
        HTTPException: Returns a 500 status code with error details if prediction fails.
    Example:
        POST /predict
        {
            "hp": 106, "attack": 110, "defense": 90,
            "sp_atk": 154, "sp_def": 90, "speed": 130
        }
        Response:
        {
            "response": "legendary"
        }
    """
    try:
        features = [[stats.hp, stats.attack, stats.defense,
                    stats.sp_atk, stats.sp_def, stats.speed]]

        prediction = predict_data(features)
        return VerdictResponse(response="legendary" if prediction[0] == 1 else "mid")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




