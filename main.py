"""
Data loading strategy (memory-efficient for Railway):
  recipes.parquet   — lean DataFrame (~180 MB RAM) for KNN search
  instructions.db   — SQLite, queried per-request for 5-10 matched rows only
Both files are built during the Railway build phase by convert_dataset.py.
"""
import os
import sqlite3
from pydantic import BaseModel, conlist
from typing import List, Optional
from model import recommend, output_recommended_recipes

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE         = os.path.dirname(os.path.abspath(__file__))
_PARQUET_PATH = os.path.join(_HERE, 'recipes.parquet')
_DB_PATH      = os.path.join(_HERE, 'instructions.db')
_CSV_PATH     = os.path.join(_HERE, 'updated.csv')   # fallback only

# ── Lazy dataset loader ───────────────────────────────────────────────────────
_dataset = None

def get_dataset():
    global _dataset
    if _dataset is None:
        import pandas as pd
        if os.path.exists(_PARQUET_PATH):
            print(f"[main] Loading recipes.parquet …", flush=True)
            _dataset = pd.read_parquet(_PARQUET_PATH)
        elif os.path.exists(_CSV_PATH):
            print(f"[main] Parquet not found — falling back to CSV …", flush=True)
            _dataset = pd.read_csv(_CSV_PATH)
        else:
            raise FileNotFoundError(
                "Neither recipes.parquet nor updated.csv found. "
                "Run convert_dataset.py to create recipes.parquet."
            )
        mem_mb = _dataset.memory_usage(deep=True).sum() // 1024 // 1024
        print(f"[main] Dataset ready: {len(_dataset):,} rows, {mem_mb} MB in RAM", flush=True)
    return _dataset


# ── Instructions lookup (SQLite, disk-based) ──────────────────────────────────
def get_instructions(row_indices):
    """
    Fetch RecipeInstructions strings for the given integer row indices.
    Reads only the matched rows from SQLite — no full load into memory.
    Returns dict {row_index: instructions_string}.
    """
    if not os.path.exists(_DB_PATH):
        return {i: '' for i in row_indices}
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    placeholders = ','.join(['?'] * len(row_indices))
    rows = conn.execute(
        f'SELECT row_num, RecipeInstructions FROM instructions '
        f'WHERE row_num IN ({placeholders})',
        list(row_indices)
    ).fetchall()
    conn.close()
    return {r[0]: (r[1] or '') for r in rows}

# Define the params model
class ParamsModel(BaseModel):
    n_neighbors: int = 5
    return_distance: bool = False

# Define the PredictionIn model
class PredictionIn(BaseModel):
    nutrition_input: conlist(float)
    ingredients: List[str] = []
    params: Optional[ParamsModel] = None
    food_type: Optional[str] = None


class Recipe(BaseModel):
    Name: str
    CookTime: str
    PrepTime: str
    TotalTime: str
    RecipeIngredientParts: List[str]
    Calories: float
    FatContent: float
    SaturatedFatContent: float
    CholesterolContent: float
    SodiumContent: float
    CarbohydrateContent: float
    FiberContent: float
    SugarContent: float
    ProteinContent: float
    RecipeInstructions: List[str]
    FoodType: str

# Define the PredictionOut model
class PredictionOut(BaseModel):
    output: Optional[List[Recipe]] = None

# ── Main prediction entry point ───────────────────────────────────────────────
def update_item(prediction_input: PredictionIn):
    recommendation_dataframe = recommend(
        get_dataset(),
        prediction_input.nutrition_input,
        prediction_input.ingredients,
        prediction_input.params.dict() if prediction_input.params else {},
        food_type=prediction_input.food_type,
    )

    if recommendation_dataframe is not None:
        # Enrich matched rows with RecipeInstructions from SQLite (disk-only lookup)
        row_indices = list(recommendation_dataframe.index)
        instructions_map = get_instructions(row_indices)
        recommendation_dataframe = recommendation_dataframe.copy()
        recommendation_dataframe['RecipeInstructions'] = (
            recommendation_dataframe.index.map(lambda i: instructions_map.get(i, ''))
        )

    output = output_recommended_recipes(recommendation_dataframe)
    return {"output": output if output is not None else None}