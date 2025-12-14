import asyncio
import csv
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)
from llama_index.embeddings.openai import OpenAIEmbedding

from app.core.config.settings.kavak_config import KavakSettings
from app.persistence.vector.collection_config import (
    CollectionType,
    get_collection_config,
)


VALUE_PROPOSITION_STRUCTURED = [
    # ========== INFORMACIÓN GENERAL ==========
    {
        "category": "general",
        "state": "general",
        "location_name": None,
        "topic": "sobre_kavak",
        "text": """KAVAK México es una plataforma de compra y venta de autos usados a los mejores precios del mercado. 
También ofrece una amplia gama de beneficios, como ayuda para conseguir la opción de "Pago a meses". 
Realiza tu pago inicial y haz la compra de tu seminuevo en poco tiempo.

Kavak México ha logrado un estatus como empresa unicornio en el país. Esto gracias a haber podido ofrecer una solución 
para tantos mexicanos que luchaban cuando tenían que comprar un auto seminuevo o tenían carros en venta. 
Buscando ofrecer su servicio a cada vez más mexicanos, Kavak México nació en el DF y fue expandiendo su negocio 
a otras ciudades de la república.

Hoy en día, Kavak cuenta con 15 sedes y 13 centros de inspección cubriendo casi todo el territorio nacional. 
El afán de Kavak sigue siendo ofrecer la mejor experiencia de compra-venta de autos en el país. De esta manera, 
quiere lograr que el momento de vender o comprar un auto seminuevo, deje de ser un dolor de cabeza para los mexicanos 
y que puedan tener un aliado en quien confiar para que gestione los trámites necesarios al mismo tiempo que ofrece beneficios reales.""",
    },
    # ========== SEDES POR ESTADO ==========
    # Puebla
    {
        "category": "sedes",
        "state": "Puebla",
        "location_name": "Kavak Explanada",
        "topic": "ubicacion_horario",
        "text": """Kavak Explanada en Puebla. Dirección: Calle Ignacio Allende 512, Santiago Momoxpan, KAVAK Puebla, Puebla, 72760. 
Horario: Lunes a Domingos: 9:00 a.m. - 6:00 p.m. Esta es una de las sedes de Kavak en el estado de Puebla donde puedes 
comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "Puebla",
        "location_name": "Kavak Las Torres",
        "topic": "ubicacion",
        "text": """Kavak Las Torres en Puebla. Dirección: Blvd. Municipio Libre 1910, Ex Hacienda Mayorazgo, 72480 Puebla, Puebla. 
Esta es una de las sedes de Kavak en el estado de Puebla donde puedes comprar o vender tu auto seminuevo.""",
    },
    # Monterrey
    {
        "category": "sedes",
        "state": "Monterrey",
        "location_name": "Kavak Punto Valle",
        "topic": "ubicacion",
        "text": """Kavak Punto Valle en Monterrey, Nuevo León. Dirección: Rio Missouri 555, Del Valle, 66220 San Pedro Garza García, N.L. Sótano 4. 
Esta es una de las sedes de Kavak en Monterrey donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "Monterrey",
        "location_name": "Kavak Nuevo Sur",
        "topic": "ubicacion",
        "text": """Kavak Nuevo Sur en Monterrey, Nuevo León. Dirección: Avenida Revolución 2703, Colonia Ladrillera, Monterrey, Nuevo León, CP: 64830. 
Esta es una de las sedes de Kavak en Monterrey donde puedes comprar o vender tu auto seminuevo.""",
    },
    # Ciudad de México
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak Plaza Fortuna",
        "topic": "ubicacion",
        "text": """Kavak Plaza Fortuna en Ciudad de México. Dirección: Av Fortuna 334, Magdalena de las Salinas, 07760, Ciudad de México, CDMX, México. 
Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak Patio Santa Fe",
        "topic": "ubicacion",
        "text": """Kavak Patio Santa Fe en Ciudad de México. Dirección: Plaza Patio Santa Fe, Sótano 3. Vasco de Quiroga 200-400, Santa Fe, 
Zedec Sta Fé, 01219, Ciudad De México. Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak Tlalnepantla",
        "topic": "ubicacion",
        "text": """Kavak Tlalnepantla en Ciudad de México. Dirección: Sentura Tlalnepantla, Perif. Blvd. Manuel Ávila Camacho 1434, 
San Andres Atenco, 54040 Tlalnepantla de Baz, Méx. Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak El Rosario Town Center",
        "topic": "ubicacion",
        "text": """Kavak El Rosario Town Center en Ciudad de México. Dirección: Av. El Rosario No. 1025 Esq. Av. Aquiles Serdán, sótano 3, 
Col. El Rosario, C.P. 02100, Azcapotzalco, Ciudad de México. Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak Cosmopol",
        "topic": "ubicacion",
        "text": """Kavak Cosmopol en Ciudad de México. Dirección: Av. José López Portillo 1, Bosques del Valle, 55717 San Francisco Coacalco, Méx. 
(sótano 2 y patio exterior). Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak Antara Fashion Hall",
        "topic": "ubicacion",
        "text": """Kavak Antara Fashion Hall en Ciudad de México. Dirección: Sótano -3 Av Moliere, Polanco II Secc, Miguel Hidalgo, 
11520 Ciudad de México, CDMX. Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "CDMX",
        "location_name": "Kavak Artz Pedregal",
        "topic": "ubicacion",
        "text": """Kavak Artz Pedregal en Ciudad de México. Dirección: Perif. Sur 3720, Jardines del Pedregal, Álvaro Obregón, 
01900 Ciudad de México, CDMX. Esta es una de las sedes de Kavak en la Ciudad de México donde puedes comprar o vender tu auto seminuevo.""",
    },
    # Guadalajara
    {
        "category": "sedes",
        "state": "Guadalajara",
        "location_name": "Kavak Midtown Guadalajara",
        "topic": "ubicacion",
        "text": """Kavak Midtown Guadalajara en Jalisco. Dirección: Av Adolfo López Mateos Nte 1133, Italia Providencia, 
44648 Guadalajara, Jal. Esta es una de las sedes de Kavak en Guadalajara donde puedes comprar o vender tu auto seminuevo.""",
    },
    {
        "category": "sedes",
        "state": "Guadalajara",
        "location_name": "Kavak Punto Sur",
        "topic": "ubicacion",
        "text": """Kavak Punto Sur en Jalisco. Dirección: Av. Punto Sur # 235, Los Gavilanes, 45645 Tlajomulco de Zúñiga, Jal. 
Sótano 2 Deck Norte. Esta es una de las sedes de Kavak en Guadalajara donde puedes comprar o vender tu auto seminuevo.""",
    },
    # Querétaro
    {
        "category": "sedes",
        "state": "Querétaro",
        "location_name": "Kavak Puerta la Victoria",
        "topic": "ubicacion",
        "text": """Kavak Puerta la Victoria en Querétaro. Dirección: Av. Constituyentes Número 40 Sótano 3, Col. Villas del Sol, 
Querétaro, Qro. 76040. Esta es una de las sedes de Kavak en Querétaro donde puedes comprar o vender tu auto seminuevo.""",
    },
    # Cuernavaca
    {
        "category": "sedes",
        "state": "Cuernavaca",
        "location_name": "Kavak Forum Cuernavaca",
        "topic": "ubicacion",
        "text": """Kavak Forum Cuernavaca en Morelos. Dirección: Jacarandas 103, Ricardo Flores Magon, Cuernavaca. México. 62370. 
Esta es una de las sedes de Kavak en Cuernavaca donde puedes comprar o vender tu auto seminuevo.""",
    },
    # ========== BENEFICIOS DE COMPRA ==========
    {
        "category": "beneficios_compra",
        "state": "general",
        "location_name": None,
        "topic": "precios_catalogo",
        "text": """Si compras con Kavak: Kavak ofrece excelentes precios, en una plataforma con miles de artículos usados de todo tipo y estilo. 
Puedes conseguir el mejor precio del mercado por los mejores autos usados. Y si el auto que buscas no aparece en su catálogo, te ayudarán a encontrarlo. 
No pierdas la oportunidad de tener el auto de tus sueños con Kavak.""",
    },
    {
        "category": "beneficios_compra",
        "state": "general",
        "location_name": None,
        "topic": "autos_certificados",
        "text": """Autos 100% certificados en Kavak: Todos los autos que salen al mercado a través de Kavak pasan por una evaluación integral 
antes de ser comprados. El proceso de inspección integral es una evaluación integral de todos los vehículos. Los inspectores especializados 
inspeccionan el diseño exterior, interior y del motor. Esto asegura la calidad del sello Kavak en todos los vehículos de la cartera de la marca.""",
    },
    # ========== BENEFICIOS DE VENTA ==========
    {
        "category": "beneficios_venta",
        "state": "general",
        "location_name": None,
        "topic": "opciones_pago_venta",
        "text": """Si vendes tu automóvil con Kavak: Puedes conseguir el mejor precio del mercado. Kavak puede ofrecer tres ofertas o una oferta: 
Ofrecer depósito, Pagar dentro de los 30 días y Pagar ahora. Depende de la demanda de su automóvil en el mercado. Si optas por realizar un envío 
y tu vehículo cumple con sus estándares de calidad, el día de la inspección puedes firmar un contrato de envío, pedirles que recojan el vehículo 
y en el momento de la venta realizan el pago acordado. Esta es la mejor oferta si no necesitas el dinero.""",
    },
    {
        "category": "beneficios_venta",
        "state": "general",
        "location_name": None,
        "topic": "vehiculo_medio_pago",
        "text": """Ofrece tu vehículo como medio de pago en Kavak: Esta plataforma te ofrece la posibilidad de ofrecer tu vehículo como medio de pago 
y pagar el resto del vehículo tu auto nuevo a meses. Para hacer esto, todo lo que necesita hacer es darle a su vehículo una cotización favorable 
y programar una inspección. En esa fecha, si su vehículo cumple con nuestros estándares de calidad, fijamos el precio final dentro del rango inmediato 
y este es el monto establecido como anticipo en la solicitud de financiamiento del vehículo de su elección.""",
    },
    # ========== FINANCIAMIENTO ==========
    {
        "category": "financiamiento",
        "state": "general",
        "location_name": None,
        "topic": "plan_pago_meses",
        "text": """Plan de pago a meses con Kavak: Con el plan de pago a meses de Kavak, podrás comprar tu auto pagando un monto mensual 
que se adapte a tus necesidades particulares. Cuentan con diferentes modelos de plan de pagos por lo que no deberás preocuparte por realizar 
trámites por tu cuenta ya que su personal calificado buscará lo mejor para ti. El primer paso para esto será conocer tu historial crediticio 
para mostrarte todas las opciones disponibles.""",
    },
    {
        "category": "financiamiento",
        "state": "general",
        "location_name": None,
        "topic": "proceso_financiamiento",
        "text": """¿Cómo funciona el plan de pago a meses con Kavak?
1. Solicita tu plan de pagos: Conoce en menos de 2 minutos las opciones que tenemos para ti.
2. Completa los datos: Ingresa tu información y valídala para recibir tu plan de pagos.
3. Realiza el primer pago: Asegura tu compra y domicilia los pagos mensuales.
4. Agenda la entrega: Firma el contrato y recibe las llaves de tu próximo auto.""",
    },
    {
        "category": "financiamiento",
        "state": "general",
        "location_name": None,
        "topic": "documentacion_financiamiento",
        "text": """¿Qué documentación necesito para financiamiento en Kavak? Para completar el proceso de solicitud, se requerirá la presentación 
de los siguientes documentos:
- Identificación oficial (INE): Deberás proporcionar una copia legible de tu identificación oficial vigente, como el Instituto Nacional Electoral 
(INE) o pasaporte. Esto servirá para verificar tu identidad y asegurar que cumples con los requisitos legales.
- Comprobante de domicilio: Deberás presentar un comprobante de domicilio reciente, como una factura de servicios públicos (agua, luz, gas) 
o un estado de cuenta bancario. Este documento debe mostrar tu nombre completo y la dirección de residencia actual.
- Comprobantes de ingresos: Se solicitarán documentos que respalden tu capacidad de pago, como recibos de nómina, estados de cuenta bancarios 
o declaraciones de impuestos. Estos documentos permitirán evaluar tu capacidad financiera para cumplir con los pagos mensuales.""",
    },
    # ========== PROCESO DIGITAL ==========
    {
        "category": "proceso",
        "state": "general",
        "location_name": None,
        "topic": "proceso_digital",
        "text": """Proceso digital de compra en Kavak: Todo el papeleo se puede realizar de forma digital, sin necesidad de visitar un centro 
ni salir de casa. El proceso es simple: simplemente ingrese a su catálogo en línea en kavak.com y seleccione el auto usado que más le guste, 
haga clic en "Me interesa" y luego seleccione la opción de cita por videollamada en la fecha y hora adecuadas. Una vez completado, nuestro 
excelente equipo de expertos se pondrá en contacto con usted a través de la última tecnología de videollamadas para mostrarle todos los detalles 
sobre su automóvil usado favorito, tanto interna como externamente, para responder todas sus preguntas sobre cómo comprarlo. Cuando finalice, 
tendrás dos opciones, proceder al pago directamente o, si te ha quedado alguna duda, agendar una reserva a domicilio donde se encargará de llevarte 
el auto hasta la puerta de tu hogar sin ningún problema ni compromiso para que continúes explorando y viéndolo más a detalle.""",
    },
    # ========== GARANTÍAS Y DEVOLUCIONES ==========
    {
        "category": "garantias",
        "state": "general",
        "location_name": None,
        "topic": "periodo_prueba_devolucion",
        "text": """Periodo de prueba y devolución en Kavak: Cuando compras un auto de ocasión tienes un periodo de prueba de 7 días o 300 km, 
en caso de que tu auto no te convenza puedes devolverlo y KAVAK te ayudará a recomprar el auto de tus sueños. Además, ofrecen una garantía de 
3 meses y la posibilidad de extenderla por un año más.""",
    },
    # ========== APP POSTVENTA ==========
    {
        "category": "app",
        "state": "general",
        "location_name": None,
        "topic": "app_postventa",
        "text": """Aplicación postventa de Kavak: En KAVAK buscan brindar a los clientes experiencias que van más allá de comprar o vender un auto. 
Desde sus inicios, siempre han apostado por la tecnología como herramienta fundamental para mejorar procesos y brindar mejores experiencias a los usuarios. 
Esto ha sido un elemento clave en el crecimiento de Kavak como compañía, y el siempre estar a la vanguardia, dejando a un lado ideas preconcebidas y antiguas, 
para dar paso a la evolución y el progreso. Por esta razón, han creado una aplicación a través de la cual cada cliente puede tener y acceder a toda la 
información detallada de su vehículo. Información detallada sobre los servicios y garantías, así como el mantenimiento del vehículo, además de facilitar 
un canal de comunicación con el equipo de KAVAK, donde recibirá un trato personalizado.""",
    },
    {
        "category": "app",
        "state": "general",
        "location_name": None,
        "topic": "funcionalidades_app",
        "text": """Funcionalidades de la App Kavak: Desde la App Kavak tienes todo lo necesario para disfrutar de tu auto y adquirir uno nuevo:
1. Aplicar garantía.
2. Amplía tu garantía a Kavak Total.
3. Agendar servicios de mantenimiento.
4. Consultar y solicitar trámites de tu auto.
5. Cotizar tu auto y obtener una oferta.
6. Consultar nuestro catálogo.

Es muy sencillo agendar un servicio de mantenimiento desde tu App Kavak. Solo tienes que ingresar con el correo y contraseña que registraste. 
Luego, en el apartado Servicios de mantenimiento encontrarás los servicios disponibles: básico, media y larga vida. Recuerda que con Kavak Total 
cuentas con dos servicios básicos incluidos a partir de tu sexto mes.""",
    },
    # ========== RESUMEN GENERAL ==========
    {
        "category": "general",
        "state": "general",
        "location_name": None,
        "topic": "resumen_empresa",
        "text": """KAVAK México es una empresa líder en la venta de autos usados en el país, ofreciendo a los clientes una experiencia única y conveniente. 
Con su amplia red de sedes en diferentes ciudades de México, brindan a los compradores la oportunidad de encontrar el auto perfecto cerca de su ubicación. 
Ya sea que estés en la Ciudad de México, Monterrey, Guadalajara o cualquier otra ciudad, KAVAK tiene presencia en múltiples sedes para atender tus necesidades. 
Además de su extensa variedad de vehículos seminuevos de alta calidad, KAVAK se destaca por su proceso de compra transparente y seguro. Su plataforma en línea 
te permite explorar el inventario, obtener información detallada de cada auto y solicitar un plan de financiamiento a medida. También ofrecen opciones de prueba 
de manejo y garantía para brindarte mayor tranquilidad al adquirir tu auto. Con sus sedes bien ubicadas en diferentes puntos del país, KAVAK facilita el acceso 
a sus servicios y te brinda la oportunidad de visitar personalmente sus instalaciones para recibir una atención personalizada por parte de su equipo de expertos.""",
    },
]


def create_car_text_representation(car: Dict[str, Any]) -> str:
    parts = []

    parts.append(
        f"Auto {car.get('make', '')} {car.get('model', '')} {car.get('year', '')}"
    )

    if car.get("version"):
        parts.append(f"Versión: {car['version']}")

    if car.get("price"):
        price = float(car["price"])
        parts.append(f"Precio: ${price:,.0f} MXN")

    if car.get("km"):
        km = int(car["km"])
        parts.append(f"Kilometraje: {km:,} km")
    features = []
    if car.get("bluetooth", "").strip().lower() in ["sí", "si", "yes", "true", "1"]:
        features.append("Bluetooth")
    if car.get("car_play", "").strip().lower() in ["sí", "si", "yes", "true", "1"]:
        features.append("Apple CarPlay")

    if features:
        parts.append(f"Características: {', '.join(features)}")

    dims = []
    if car.get("largo"):
        dims.append(f"Largo: {car['largo']} mm")
    if car.get("ancho"):
        dims.append(f"Ancho: {car['ancho']} mm")
    if car.get("altura"):
        dims.append(f"Altura: {car['altura']} mm")

    if dims:
        parts.append(f"Dimensiones: {', '.join(dims)}")

    if car.get("stock_id"):
        parts.append(f"ID de stock: {car['stock_id']}")

    return ". ".join(parts)


async def load_catalog_collection(
    csv_path: Path,
    qdrant_client: QdrantClient,
    embedding_model: OpenAIEmbedding,
    collection_config,
) -> None:
    print(f"\nLoading catalog collection: {collection_config.name}")

    collections = qdrant_client.get_collections()
    collection_names = [c.name for c in collections.collections]

    if collection_config.name not in collection_names:
        print(f"   Creating collection: {collection_config.name}")
        qdrant_client.create_collection(
            collection_name=collection_config.name,
            vectors_config=VectorParams(
                size=collection_config.vector_size,
                distance=collection_config.distance,
            ),
        )
    else:
        print(f"   Collection already exists, will update: {collection_config.name}")

    print("   Creating payload indexes for filtering...")
    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="price",
            field_schema=PayloadSchemaType.FLOAT,
        )
        print("   Created index for 'price'")
    except Exception as e:
        print(f"   Index for 'price' may already exist: {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="year",
            field_schema=PayloadSchemaType.INTEGER,
        )
        print("   Created index for 'year'")
    except Exception as e:
        print(f"   Index for 'year' may already exist: {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="km",
            field_schema=PayloadSchemaType.INTEGER,
        )
        print("   Created index for 'km'")
    except Exception as e:
        print(f"   Index for 'km' may already exist: {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="make",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        print("   Created index for 'make'")
    except Exception as e:
        print(f"   Index for 'make' may already exist: {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="model",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        print("   Created index for 'model'")
    except Exception as e:
        print(f"   Index for 'model' may already exist: {e}")

    cars = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cars.append(row)

    print(f"   Found {len(cars)} cars in CSV")

    batch_size = 50
    points = []

    for i, car in enumerate(cars):
        text = create_car_text_representation(car)

        embedding = await embedding_model.aget_text_embedding(text)

        stock_id = car.get("stock_id")
        point_id = int(stock_id) if stock_id and stock_id.isdigit() else i
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "stock_id": stock_id,
                "make": car.get("make", ""),
                "model": car.get("model", ""),
                "year": int(car["year"]) if car.get("year") else None,
                "version": car.get("version", ""),
                "price": float(car["price"]) if car.get("price") else None,
                "km": int(car["km"]) if car.get("km") else None,
                "bluetooth": car.get("bluetooth", "").strip().lower()
                in ["sí", "si", "yes", "true", "1"],
                "car_play": car.get("car_play", "").strip().lower()
                in ["sí", "si", "yes", "true", "1"],
                "largo": float(car["largo"]) if car.get("largo") else None,
                "ancho": float(car["ancho"]) if car.get("ancho") else None,
                "altura": float(car["altura"]) if car.get("altura") else None,
                "text": text,
            },
        )
        points.append(point)

        if len(points) >= batch_size:
            qdrant_client.upsert(
                collection_name=collection_config.name,
                points=points,
            )
            points = []

    if points:
        qdrant_client.upsert(
            collection_name=collection_config.name,
            points=points,
        )


async def load_value_prop_collection(
    qdrant_client: QdrantClient,
    embedding_model: OpenAIEmbedding,
    collection_config,
) -> None:
    collections = qdrant_client.get_collections()
    collection_names = [c.name for c in collections.collections]

    if collection_config.name not in collection_names:
        qdrant_client.create_collection(
            collection_name=collection_config.name,
            vectors_config=VectorParams(
                size=collection_config.vector_size,
                distance=collection_config.distance,
            ),
        )

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        print(f"error {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="state",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        print(f"error {e}")
    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="topic",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        print(f"error {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="location_name",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        print(f"error {e}")

    try:
        qdrant_client.create_payload_index(
            collection_name=collection_config.name,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        print(f"error {e}")

    batch_size = 50
    points = []

    for i, content_item in enumerate(VALUE_PROPOSITION_STRUCTURED):
        text = content_item["text"]

        embedding = await embedding_model.aget_text_embedding(text)

        point = PointStruct(
            id=i,
            vector=embedding,
            payload={
                "text": text,
                "category": content_item["category"],
                "state": content_item["state"],
                "location_name": content_item["location_name"],
                "topic": content_item["topic"],
                "source": "kavak_blog_sedes",
                "chunk_index": i,
            },
        )
        points.append(point)

        if len(points) >= batch_size:
            print(f"   Uploading batch {i // batch_size + 1} ({len(points)} points)...")
            qdrant_client.upsert(
                collection_name=collection_config.name,
                points=points,
            )
            points = []

    if points:
        print(f"   Uploading final batch ({len(points)} points)...")
        qdrant_client.upsert(
            collection_name=collection_config.name,
            points=points,
        )

    categories = {}
    states = {}
    for item in VALUE_PROPOSITION_STRUCTURED:
        cat = item["category"]
        state = item["state"]
        categories[cat] = categories.get(cat, 0) + 1
        states[state] = states.get(state, 0) + 1


async def main():
    settings = KavakSettings()

    is_cloud = "cloud.qdrant.io" in settings.qdrant.HOST
    qdrant_client = QdrantClient(
        **(
            {"url": f"https://{settings.qdrant.HOST}"}
            if is_cloud
            else {
                "host": settings.qdrant.HOST,
                "port": settings.qdrant.PORT,
                "https": settings.qdrant.USE_TLS,
            }
        ),
        api_key=settings.qdrant.API_KEY,
    )

    embedding_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=settings.llm.OPENAI_API_KEY,
    )

    catalog_config = get_collection_config(CollectionType.KAVAK_CATALOG)
    value_prop_config = get_collection_config(CollectionType.KAVAK_VALUE_PROP)

    csv_path = Path(__file__).parent / "sample_caso_ai_engineer.csv"

    await load_catalog_collection(
        csv_path=csv_path,
        qdrant_client=qdrant_client,
        embedding_model=embedding_model,
        collection_config=catalog_config,
    )

    await load_value_prop_collection(
        qdrant_client=qdrant_client,
        embedding_model=embedding_model,
        collection_config=value_prop_config,
    )

    print("success")


if __name__ == "__main__":
    asyncio.run(main())
