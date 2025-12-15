def build_car_preferences_extraction_prompt(preferences: str) -> str:
    return f"""Analiza este texto y extrae información sobre el auto mencionado: "{preferences}"

IMPORTANTE: 
- Si menciona una marca Y modelo (ej: "Toyota Corolla", "el Corolla", "toyota corolla", "corolla"), extrae AMBOS: brand y model.
- Si solo menciona marca (ej: "Toyota"), extrae solo brand.
- Si menciona año específico, extrae year_min y year_max con ese año.
- Ignora preguntas sobre características (Bluetooth, CarPlay) - solo extrae marca, modelo, año.

Extrae: marca (brand), modelo (model), año (year_min/year_max si se menciona).

Ejemplos:
- "el toyota corolla tiene bluetooth?" → brand: "Toyota", model: "Corolla"
- "toyota corolla 2020" → brand: "Toyota", model: "Corolla", year_min: 2020, year_max: 2020
- "corolla" → brand: "Toyota", model: "Corolla" (si puedes inferir la marca)

Responde en formato JSON válido."""
