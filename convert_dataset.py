"""
Convert updated.csv into two memory-efficient files:
  recipes.parquet   — all columns EXCEPT RecipeInstructions, float32 numerics, category FoodType
                      (~180 MB in RAM instead of ~700 MB)
  instructions.db   — SQLite with {row_num, RecipeInstructions}
                      queried per-request for only the matched 5-10 rows

Run during Railway build phase (see nixpacks.toml).
"""
import pandas as pd
import sqlite3
import os
import sys

CSV_PATH     = 'updated.csv'
PARQUET_PATH = 'recipes.parquet'
DB_PATH      = 'instructions.db'

MAIN_COLS = [
    'Name', 'CookTime', 'PrepTime', 'TotalTime',
    'RecipeIngredientParts',
    'Calories', 'FatContent', 'SaturatedFatContent', 'CholesterolContent',
    'SodiumContent', 'CarbohydrateContent', 'FiberContent',
    'SugarContent', 'ProteinContent',
    'FoodType',
]

NUMERIC_COLS = [
    'Calories', 'FatContent', 'SaturatedFatContent', 'CholesterolContent',
    'SodiumContent', 'CarbohydrateContent', 'FiberContent',
    'SugarContent', 'ProteinContent',
]

if not os.path.exists(CSV_PATH):
    print(f"[convert] ERROR: {CSV_PATH} not found — aborting.", flush=True)
    sys.exit(1)

print(f"[convert] Loading {CSV_PATH} …", flush=True)
df = pd.read_csv(
    CSV_PATH,
    usecols=lambda c: c in MAIN_COLS + ['RecipeInstructions'],
    dtype={c: 'float32' for c in NUMERIC_COLS},
    low_memory=False,
)
df = df.reset_index(drop=True)
print(f"[convert] {len(df):,} rows loaded.", flush=True)

# ── Save main parquet (no RecipeInstructions) ─────────────────────────────────
df_main = df[MAIN_COLS].copy()
df_main['FoodType'] = df_main['FoodType'].astype('category')
df_main.to_parquet(PARQUET_PATH, index=True, compression='snappy')
mem_mb = df_main.memory_usage(deep=True).sum() // 1024 // 1024
print(f"[convert] Saved {PARQUET_PATH}  ({mem_mb} MB in-memory footprint)", flush=True)

# ── Save instructions SQLite ──────────────────────────────────────────────────
print(f"[convert] Building {DB_PATH} …", flush=True)
conn = sqlite3.connect(DB_PATH)
conn.execute('DROP TABLE IF EXISTS instructions')
conn.execute('''
    CREATE TABLE instructions (
        row_num INTEGER PRIMARY KEY,
        RecipeInstructions TEXT
    )
''')
instructions = df['RecipeInstructions'].fillna('').tolist()
conn.executemany(
    'INSERT INTO instructions VALUES (?, ?)',
    enumerate(instructions)
)
conn.execute('PRAGMA journal_mode=WAL')
conn.commit()
conn.close()
db_mb = os.path.getsize(DB_PATH) // 1024 // 1024
print(f"[convert] Saved {DB_PATH}  ({db_mb} MB on disk)", flush=True)

# ── Remove original CSV to free disk space ────────────────────────────────────
os.remove(CSV_PATH)
print(f"[convert] Deleted {CSV_PATH}. Conversion complete.", flush=True)
