def build_car_preferences_extraction_prompt(preferences: str) -> str:
    return f"""Analiza este texto y extrae información sobre el auto mencionado: "{preferences}"

IMPORTANTE: 
- Si menciona una marca Y modelo (ej: "Toyota Corolla", "el Corolla", "toyota corolla", "corolla"), extrae AMBOS: brand y model.
- Si solo menciona marca (ej: "Toyota"), extrae solo brand.
- Si menciona año específico, extrae year_min y year_max con ese año.
- Ignora preguntas sobre características (Bluetooth, CarPlay) - solo extrae marca, modelo, año.
- DETECTA INTENCIONES COMPARATIVAS: Si pregunta por "menor/más bajo/mínimo kilometraje" → order_by: "mileage_asc"
- Si pregunta por "mayor/más alto/máximo kilometraje" → order_by: "mileage_desc"
- Si pregunta por "más barato/menor precio/precio mínimo" → order_by: "price_asc"
- Si pregunta por "más caro/mayor precio/precio máximo" → order_by: "price_desc"
- Si pregunta por "más nuevo/año más reciente" → order_by: "year_desc"
- Si pregunta por "más viejo/año más antiguo" → order_by: "year_asc"

Extrae: marca (brand), modelo (model), año (year_min/year_max si se menciona), order_by (si hay intención comparativa).

Ejemplos:
- "el toyota corolla tiene bluetooth?" → brand: "Toyota", model: "Corolla"
- "toyota corolla 2020" → brand: "Toyota", model: "Corolla", year_min: 2020, year_max: 2020
- "corolla" → brand: "Toyota", model: "Corolla" (si puedes inferir la marca)
- "cuál es el auto con menor kilometraje?" → order_by: "mileage_asc"
- "auto más barato" → order_by: "price_asc"
- "toyota con menor kilometraje" → brand: "Toyota", order_by: "mileage_asc"

Responde en formato JSON válido."""
