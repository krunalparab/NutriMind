import numpy as np
import re
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

# Named nutrition columns used for KNN — independent of column position
NUTRITION_COLS = [
    'Calories', 'FatContent', 'SaturatedFatContent', 'CholesterolContent',
    'SodiumContent', 'CarbohydrateContent', 'FiberContent',
    'SugarContent', 'ProteinContent',
]


def scaling(dataframe):
    scaler = StandardScaler()
    prep_data = scaler.fit_transform(dataframe[NUTRITION_COLS].to_numpy())
    return prep_data, scaler

def nn_predictor(prep_data):
    neigh = NearestNeighbors(metric='cosine',algorithm='brute')
    neigh.fit(prep_data)
    return neigh

def build_pipeline(neigh,scaler,params):
    transformer = FunctionTransformer(neigh.kneighbors,kw_args=params)
    pipeline=Pipeline([('std_scaler',scaler),('NN',transformer)])
    return pipeline

def extract_data(dataframe,ingredients):
    extracted_data=dataframe.copy()
    if ingredients:
        extracted_data=extract_ingredient_filtered_data(extracted_data,ingredients)
    return extracted_data
    
def extract_ingredient_filtered_data(dataframe, ingredients):
    extracted_data = dataframe.copy()
    
    # Create a regex pattern to match any of the ingredients
    regex_string = '|'.join(map(re.escape, ingredients))  # Use '|' to create an OR condition
    
    # Filter out rows that contain any of the specified ingredients
    extracted_data = extracted_data[~extracted_data['RecipeIngredientParts'].str.contains(regex_string, regex=True, flags=re.IGNORECASE)]
    
    return extracted_data



# def recommend(dataframe,_input,ingredients=[],params={'n_neighbors':5,'return_distance':False}):
#         extracted_data=extract_data(dataframe,ingredients)
#         if extracted_data.shape[0]>=params['n_neighbors']:
#             prep_data,scaler=scaling(extracted_data)
#             neigh=nn_predictor(prep_data)
#             pipeline=build_pipeline(neigh,scaler,params)
#             return apply_pipeline(pipeline,_input,extracted_data)
#         else:
#             return None

# def train_random_forest(dataframe):
#     """Train Random Forest model to rank recipes."""
#     nutrition_features = dataframe.iloc[:, 6:15]  
#     heuristic_score = dataframe["ProteinContent"] - dataframe["SugarContent"]  # Example heuristic
    
#     rf = RandomForestRegressor(n_estimators=100, random_state=42)
#     rf.fit(nutrition_features, heuristic_score)
    
#     return rf

def apply_pipeline(pipeline,_input,extracted_data):
    _input=np.array(_input).reshape(1,-1)
    return extracted_data.iloc[pipeline.transform(_input)[0]]

def recommend(dataframe, _input, ingredients=[], params={'n_neighbors': 5, 'return_distance': False}, food_type=None):
    extracted_data = extract_data(dataframe, ingredients)


    if food_type:
        extracted_data = extracted_data[extracted_data['FoodType'] == food_type]
        # print(extracted_data)
    if extracted_data.shape[0] >= params['n_neighbors']:
        prep_data, scaler = scaling(extracted_data)
        neigh = nn_predictor(prep_data)
        pipeline = build_pipeline(neigh, scaler, params)
        return apply_pipeline(pipeline, _input, extracted_data)
    else:
        return None

def extract_quoted_strings(s):
    strings = re.findall(r'"([^"]*)"', s)
    return strings

def output_recommended_recipes(dataframe):
    if dataframe is not None:
        output=dataframe.copy()
        output=output.to_dict("records")
        for recipe in output:
            recipe['RecipeIngredientParts']=extract_quoted_strings(recipe['RecipeIngredientParts'])
            recipe['RecipeInstructions']=extract_quoted_strings(recipe['RecipeInstructions'])
    else:
        output=None
    return output

# import numpy as np
# import re
# import pandas as pd
# from sklearn.preprocessing import StandardScaler
# from sklearn.neighbors import NearestNeighbors
# from sklearn.pipeline import Pipeline
# from sklearn.preprocessing import FunctionTransformer
# from sklearn.ensemble import RandomForestRegressor

# def scaling(dataframe):
#     scaler = StandardScaler()
#     prep_data = scaler.fit_transform(dataframe.iloc[:, 6:15].to_numpy())  # Normalize nutrition data
#     return prep_data, scaler

# def nn_predictor(prep_data):
#     neigh = NearestNeighbors(metric='cosine', algorithm='brute')
#     neigh.fit(prep_data)
#     return neigh

# def build_pipeline(neigh, scaler, params):
#     transformer = FunctionTransformer(neigh.kneighbors, kw_args=params)
#     pipeline = Pipeline([('std_scaler', scaler), ('NN', transformer)])
#     return pipeline

# def extract_data(dataframe, ingredients):
#     extracted_data = dataframe.copy()
#     extracted_data = extract_ingredient_filtered_data(extracted_data, ingredients)
#     return extracted_data

# def extract_ingredient_filtered_data(dataframe, ingredients):
#     extracted_data = dataframe.copy()
#     regex_string = ''.join(map(lambda x: f'(?=.*{x})', ingredients))
#     extracted_data = extracted_data[extracted_data['RecipeIngredientParts'].str.contains(regex_string, regex=True, flags=re.IGNORECASE)]
#     return extracted_data

# def apply_pipeline(pipeline, _input, extracted_data):
#     _input = np.array(_input).reshape(1, -1)
#     return extracted_data.iloc[pipeline.transform(_input)[0]]

# 

# def recommend(dataframe, _input, ingredients=[], params={'n_neighbors': 5, 'return_distance': False}):
#     extracted_data = extract_data(dataframe, ingredients)
    
#     if extracted_data.shape[0] >= params['n_neighbors']:
#         prep_data, scaler = scaling(extracted_data)
#         neigh = nn_predictor(prep_data)
#         pipeline = build_pipeline(neigh, scaler, params)

#         recommended_recipes = apply_pipeline(pipeline, _input, extracted_data).copy()
        
#         # Train Random Forest and rank recommendations
#         rf = train_random_forest(extracted_data)
#         nutrition_features = recommended_recipes.iloc[:, 6:15]
#         recommended_recipes["PredictedScore"] = rf.predict(nutrition_features)
#         recommended_recipes = recommended_recipes.sort_values(by="PredictedScore", ascending=False)
        
#         return recommended_recipes
#     else:
#         return None

# def extract_quoted_strings(s):
#     strings = re.findall(r'"([^"]*)"', s)
#     return strings

# def output_recommended_recipes(dataframe):
#     if dataframe is not None:
#         output = dataframe.copy().to_dict("records")
#         for recipe in output:
#             recipe['RecipeIngredientParts'] = extract_quoted_strings(recipe['RecipeIngredientParts'])
#             recipe['RecipeInstructions'] = extract_quoted_strings(recipe['RecipeInstructions'])
#     else:
#         output = None
#     return output
