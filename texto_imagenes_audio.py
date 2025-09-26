import streamlit as st
import requests
import base64
import io
import time
from PIL import Image
from io import BytesIO
import json
import os
from typing import Optional, Dict, Any

# Configuración de la página
st.set_page_config(
    page_title="Generador de Contenido Multimedia - Claude & Flux",
    page_icon="🎨",
    layout="wide"
)

# Inicializar session state para mantener resultados
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = {}

if 'generation_complete' not in st.session_state:
    st.session_state.generation_complete = False

# Título principal
st.title("🎨 Generador de Contenido Multimedia")
st.markdown("*Powered by Claude Sonnet 4 & Flux - Transforma tus ideas en texto, imágenes y audio*")

# Sidebar para configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # APIs keys
    st.subheader("Claves de API")
    anthropic_api_key = st.text_input("Anthropic API Key", type="password", help="Para generación de texto con Claude Sonnet 4")
    bfl_api_key = st.text_input("Black Forest Labs API Key", type="password", help="Para generación de imágenes con Flux")
    openai_api_key = st.text_input("OpenAI API Key", type="password", help="Para generación de audio TTS")
    
    # Configuraciones del modelo
    st.subheader("Configuración de Modelos")
    
    # Modelo de Claude
    claude_model = st.selectbox(
        "Modelo de Claude",
        ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
        index=0,
        help="Claude Sonnet 4 es el más reciente y avanzado"
    )
    
    # Configuración de Flux
    flux_model = st.selectbox(
        "Modelo de Flux",
        ["flux-pro-1.1", "flux-pro-1.1-ultra"],
        index=0,
        help="Pro 1.1 permite control de dimensiones, Ultra es para máxima calidad"
    )
    
    flux_steps = st.slider("Pasos de generación (Flux)", 1, 50, 25, help="Más pasos = mejor calidad pero más tiempo")
    
    # Estilo de imagen
    image_style = st.selectbox(
        "Estilo de imagen",
        ["photorealistic", "digital-art", "cinematic", "documentary", "portrait"],
        index=0,
        help="Estilo visual para la generación de imágenes"
    )
    
    # Configuración de audio
    voice_model = st.selectbox(
        "Voz para Audio",
        ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        index=0
    )
    
    # Configuraciones adicionales
    st.subheader("Configuraciones Avanzadas")
    max_tokens_claude = st.number_input("Max tokens Claude", 500, 4000, 2000)
    
    # Configuraciones específicas según modelo de Flux
    if flux_model == "flux-pro-1.1":
        image_width = st.selectbox("Ancho de imagen", [512, 768, 1024, 1344], index=2)
        image_height = st.selectbox("Alto de imagen", [512, 768, 1024, 1344], index=2)
    else:  # Ultra
        st.info("💡 Flux Ultra maneja las dimensiones automáticamente")
        image_width = 1024  # Valor por defecto para Ultra
        image_height = 1024

# Función para generar texto con Claude Sonnet 4
def generate_text_claude(prompt: str, content_type: str, api_key: str, model: str, max_tokens: int) -> Optional[str]:
    """Genera contenido de texto usando Claude Sonnet 4 de Anthropic"""
    try:
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Prompts específicos y mejorados para Claude (AMPLIADOS)
        system_prompts = {
            "ejercicio": """Eres un experto educador con amplia experiencia pedagógica. Tu tarea es crear ejercicios educativos que sean:
- Estructurados y progresivos
- Adaptados al nivel apropiado
- Incluyan explicaciones claras
- Contengan ejemplos prácticos
- Fomenten el pensamiento crítico
Formato: Título, objetivos, desarrollo paso a paso, ejercicios prácticos y evaluación.""",
            
            "artículo": """Eres un periodista y escritor especializado en crear artículos informativos de alta calidad. Tu contenido debe ser:
- Bien investigado y fundamentado
- Estructurado con introducción, desarrollo y conclusión
- Objetivo y equilibrado
- Accesible para el público general
- Incluir datos relevantes y contexto necesario
Formato: Titular atractivo, lead informativo, desarrollo en secciones y conclusión impactante.""",
            
            "texto": """Eres un escritor creativo versátil. Tu objetivo es crear textos que sean:
- Originales y creativos
- Bien estructurados y fluidos
- Adaptados al propósito específico
- Engaging y memorable
- Con estilo apropiado para el contenido
Formato: Libre, adaptado al tipo de texto solicitado.""",
            
            "relato": """Eres un narrador experto en storytelling. Tus relatos deben incluir:
- Desarrollo sólido de personajes
- Trama envolvente con conflicto y resolución
- Ambientación vivida y detallada
- Diálogos naturales y efectivos
- Ritmo narrativo apropiado
- Final satisfactorio
Formato: Estructura narrativa clásica con introducción, desarrollo, clímax y desenlace.""",
            
            "diálogo situacional": """Eres un experto en creación de contenido educativo para idiomas. Tu tarea es crear diálogos situacionales que sean:
- Naturales y auténticos
- Apropiados para el contexto
- Con vocabulario cotidiano útil
- Breves pero completos (6-10 líneas)
- Incluyan expresiones idiomáticas comunes
Formato: Diálogo breve + lista de 5-7 expresiones clave con explicación.""",
            
            "artículo cultural": """Eres un escritor especializado en divulgación cultural. Tu contenido debe ser:
- Informativo y atractivo (120-150 palabras)
- Claro y accesible
- Con ejemplos concretos
- Que despierte interés cultural
- Educativo pero entretenido
Formato: Artículo divulgativo + glosario de 5 palabras clave.""",
            
            "artículo de actualidad": """Eres un periodista especializado en adaptar noticias para diferentes audiencias. Tu contenido debe ser:
- Claro y directo (80-120 palabras)
- Con lenguaje sencillo
- Bien estructurado
- Objetivo y factual
- Fácil de comprender
Formato: Noticia simplificada + 2-3 preguntas de comprensión.""",
            
            "artículo biográfico": """Eres un biógrafo especializado en crear perfiles concisos. Tu contenido debe incluir:
- Información esencial (100-120 palabras)
- Fechas y logros clave
- Relevancia cultural o histórica
- Datos verificables
- Un elemento curioso o interesante
Formato: Mini-biografía + dato curioso final.""",
            
            "clip de noticias": """Eres un editor de noticias especializado en contenido ultrabreve. Tu tarea es crear:
- Textos muy concisos (40-60 palabras por noticia)
- Información directa y clara
- Vocabulario comprensible
- Estilo telegráfico pero completo
- 5 noticias por tema
Formato: 5 clips de noticias + frase resumen simple.""",
            
            "pregunta de debate": """Eres un moderador experto en generar debates constructivos. Tu contenido debe:
- Plantear dilemas interesantes
- Ser breve pero provocativo (2-3 frases)
- Usar lenguaje sencillo
- Estimular múltiples perspectivas
- Terminar con pregunta abierta
Formato: Introducción del tema + pregunta de debate abierta.""",
            
            "receta de cocina": """Eres un chef educador especializado en recetas sencillas. Tu contenido debe incluir:
- Instrucciones claras (80-100 palabras)
- Lista de ingredientes específica
- Pasos en imperativo
- Técnicas básicas explicadas
- Consejos útiles
Formato: Lista de ingredientes + 3-4 pasos de preparación.""",
            
            "post de redes sociales": """Eres un community manager especializado en contenido educativo para redes. Tu contenido debe ser:
- Muy breve (40-60 palabras)
- Tono informal y cercano
- Incluir emojis apropiados
- 1-2 hashtags relevantes
- Lenguaje coloquial auténtico
Formato: Post informal + traducción de expresiones coloquiales.""",
            
            "trivia cultural": """Eres un creador de contenido educativo especializado en preguntas de cultura general. Tu contenido debe incluir:
- 6 preguntas de opción múltiple
- 4 opciones (A-D) por pregunta
- Respuesta correcta marcada
- Explicación breve de cada respuesta
- Nivel apropiado de dificultad
Formato: Batería de preguntas + explicaciones de respuestas correctas."""
        }
        
        # Instrucciones específicas según el tipo de contenido
        def get_content_specific_instructions(content_type):
            instructions = {
                "ejercicio": "Crea un ejercicio educativo completo con estructura clara.",
                
                "artículo": "Redacta un artículo informativo completo y bien estructurado.",
                
                "texto": "Crea un texto apropiado para el tema y propósito indicado.",
                
                "relato": "Escribe un relato completo con estructura narrativa clásica.",
                
                "diálogo situacional": """Escribe un diálogo breve (6–10 líneas) entre dos personajes en el contexto indicado. Incluye expresiones naturales del idioma, vocabulario cotidiano y un tono realista. Añade debajo una lista con 5–7 expresiones clave con traducción sencilla.""",
                
                "artículo cultural": """Redacta un artículo cultural de 120–150 palabras sobre el tema indicado. Usa un estilo divulgativo, frases cortas y vocabulario accesible. Añade un pequeño glosario de 5 palabras con definición sencilla.""",
                
                "artículo de actualidad": """Escribe un artículo breve de actualidad de 80–120 palabras sobre el tema/noticia indicada. Usa un estilo sencillo y claro. Añade 2–3 preguntas de comprensión al final.""",
                
                "artículo biográfico": """Crea una biografía breve de 100–120 palabras sobre la persona indicada. Incluye 3–4 hechos clave (fechas, logros, importancia). Añade una línea final con 'Dato curioso'.""",
                
                "clip de noticias": """Escribe un clip de 5 noticias en 40–60 palabras cada una sobre el tema indicado. Debe ser directo, claro y con vocabulario comprensible. Añade una frase con la idea principal en lenguaje aún más simple.""",
                
                "pregunta de debate": """Plantea una pregunta de debate en 2–3 frases sobre el tema indicado. El texto debe introducir la situación brevemente y terminar con una pregunta abierta. Nivel de idioma sencillo, para fomentar conversación.""",
                
                "receta de cocina": """Escribe una receta breve de 80–100 palabras sobre cómo preparar el plato indicado. Incluye una lista corta de ingredientes y 3–4 pasos en imperativo (ej.: corta, mezcla, añade).""",
                
                "post de redes sociales": """Crea un post de redes sociales de 40–60 palabras sobre el tema indicado. Usa tono informal, emojis y 1–2 hashtags. Añade debajo la traducción literal de 3 expresiones coloquiales que aparezcan.""",
                
                "trivia cultural": """Escribe una batería de 6 preguntas de trivial cultural sobre el tema indicado. Ofrece 4 opciones (A–D) y marca la correcta. Añade una explicación breve (1 frase) de por qué la respuesta es la correcta."""
            }
            return instructions.get(content_type, instructions["texto"])
        
        user_message = f"""Crea un {content_type} sobre: {prompt}

{get_content_specific_instructions(content_type)}

Por favor, asegúrate de que el contenido sea:
1. Completo y bien desarrollado según las especificaciones
2. Apropiado para el tipo de contenido solicitado
3. Interesante y bien escrito
4. Listo para ser presentado como contenido final

El {content_type} debe seguir exactamente el formato y extensión indicados."""
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "system": system_prompts.get(content_type, system_prompts["texto"]),
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data["content"][0]["text"]
        else:
            st.error(f"Error generando texto con Claude: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error en la generación de texto con Claude: {str(e)}")
        return None

# Nueva función para generar prompt visual con Claude
def generate_visual_prompt_with_claude(text_content: str, content_type: str, style: str, api_key: str, model: str) -> Optional[str]:
    """Genera un prompt visual optimizado usando Claude basado en el contenido generado"""
    try:
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # System prompt especializado para generación de prompts visuales
        system_prompt = """Eres un experto en generación de prompts para modelos de AI de imágenes, específicamente para Flux. Tu tarea es analizar contenido de texto y crear prompts visuales optimizados en inglés.

REGLAS IMPORTANTES:
1. El prompt DEBE estar en inglés perfecto
2. Debe ser específico y descriptivo visualmente
3. Incluir términos técnicos de fotografía/arte cuando sea apropiado
4. Adaptar al estilo solicitado
5. Ser conciso pero detallado (máximo 150 palabras)
6. NO reproducir texto del contenido, solo elementos visuales

ESTRUCTURA DEL PROMPT:
[Descripción visual principal] + [Estilo técnico] + [Calidad/Resolución] + [Elementos compositivos]"""
# Instrucciones específicas por tipo de contenido (AMPLIADAS)
        content_instructions = {
            "ejercicio": """Analiza este ejercicio educativo y crea un prompt visual que represente:
- La materia/tema principal del ejercicio
- Un ambiente educativo apropiado (aula, laboratorio, biblioteca, etc.)
- Elementos visuales que complementen el aprendizaje
- Personas estudiando o practicando el tema si es relevante
- Materiales educativos relacionados

Evita incluir texto específico del ejercicio, solo elementos visuales educativos.""",
            
            "artículo": """Analiza este artículo y crea un prompt visual que represente:
- El tema central o concepto principal
- Elementos que ilustren la información clave
- Un contexto visual apropiado para el tema
- Objetos, personas o lugares relevantes al contenido
- Una composición que transmita el mensaje principal

Evita texto específico, enfócate en elementos visuales informativos.""",
            
            "texto": """Analiza este texto y crea un prompt visual que capture:
- El tema o concepto principal
- El tono y ambiente del contenido
- Elementos visuales que complementen el mensaje
- Una composición apropiada para el propósito del texto
- Elementos que refuercen visualmente la idea principal

Enfócate en la esencia visual del contenido.""",
            
            "relato": """Analiza este relato y crea un prompt visual que capture:
- La escena más representativa o impactante
- Los personajes principales (sin nombres específicos)
- La ambientación y época de la historia
- El mood/atmósfera del relato
- Elementos narrativos clave visualmente

Crea una escena cinematográfica que represente el relato.""",
            
            "diálogo situacional": """Analiza este diálogo situacional y crea un prompt visual que muestre:
- El contexto/lugar donde ocurre la conversación
- Dos personas conversando de manera natural
- El ambiente apropiado (cafetería, aeropuerto, oficina, etc.)
- Elementos que refuercen el contexto situacional
- Una escena realista y cotidiana

Representa visualmente la situación del diálogo.""",
            
            "artículo cultural": """Analiza este artículo cultural y crea un prompt visual que represente:
- La tradición, costumbre o elemento cultural principal
- Escenas típicas relacionadas con la cultura descrita
- Personas participando en actividades culturales
- Elementos visuales representativos (objetos, lugares, vestimentas)
- Un ambiente que refleje la identidad cultural

Captura la esencia visual de la cultura descrita.""",
            
            "artículo de actualidad": """Analiza este artículo de actualidad y crea un prompt visual que muestre:
- El tema principal de la noticia
- Elementos visuales que ilustren la información
- Un contexto actual y contemporáneo
- Personas, lugares u objetos relacionados con la noticia
- Una composición informativa y clara

Representa visualmente el contenido noticioso.""",
            
            "artículo biográfico": """Analiza este artículo biográfico y crea un prompt visual que incluya:
- Un retrato o representación de la época de la persona
- Elementos relacionados con sus logros principales
- El contexto histórico o profesional relevante
- Objetos o símbolos asociados con su trabajo/vida
- Una composición que honre su legado

Crea una representación visual dignificante del personaje.""",
            
            "clip de noticias": """Analiza estos clips de noticias y crea un prompt visual que muestre:
- Una composición estilo noticiero o medio de comunicación
- Elementos gráficos informativos modernos
- Un ambiente de sala de redacción o estudio de noticias
- Personas trabajando en medios de comunicación
- Una estética profesional y contemporánea

Representa el mundo del periodismo y las noticias.""",
            
            "pregunta de debate": """Analiza esta pregunta de debate y crea un prompt visual que represente:
- Personas en situación de diálogo o debate
- Un ambiente apropiado para la discusión (aula, mesa redonda, etc.)
- Elementos que sugieran intercambio de ideas
- Una composición que invite al diálogo
- Diversidad de perspectivas visuales

Crea una escena que fomente la conversación.""",
            
            "receta de cocina": """Analiza esta receta y crea un prompt visual que muestre:
- Los ingredientes principales de la receta
- Una cocina acogedora y bien equipada
- El proceso de cocinar o el plato terminado
- Utensilios de cocina apropiados
- Una presentación apetitosa y profesional

Representa visualmente la experiencia culinaria.""",
            
            "post de redes sociales": """Analiza este post y crea un prompt visual que capture:
- El estilo visual típico de redes sociales
- Elementos modernos y contemporáneos
- Una estética atractiva y "instagrameable"
- Personas usando dispositivos móviles o en situaciones sociales
- Colores vibrantes y composición dinámica

Crea una imagen perfecta para redes sociales.""",
            
            "trivia cultural": """Analiza esta trivia cultural y crea un prompt visual que represente:
- Un ambiente de quiz o juego educativo
- Elementos relacionados con el tema de las preguntas
- Personas participando en actividades de conocimiento
- Libros, mapas, o símbolos culturales relevantes
- Una composición educativa y atractiva

Representa el mundo del conocimiento y la cultura general."""
        }
        
        # Adaptaciones por estilo visual
        style_adaptations = {
            "photorealistic": "Como una fotografía profesional realista, con iluminación natural, alta definición, composición fotográfica, detalles nítidos",
            "digital-art": "Como arte digital de alta calidad, colores vibrantes, composición artística, estilo ilustrativo moderno, diseño profesional",
            "cinematic": "Con composición cinematográfica, iluminación dramática, profundidad de campo, ambiente de película, producción de alta calidad",
            "documentary": "Estilo documental auténtico, fotografía candida, iluminación natural, ambiente real, calidad periodística",
            "portrait": "Enfoque retrato profesional, iluminación de estudio, composición centrada en personas, calidad profesional"
        }
        
        user_message = f"""CONTENIDO A ANALIZAR:
{text_content}

TIPO DE CONTENIDO: {content_type}
ESTILO DESEADO: {style}

{content_instructions.get(content_type, content_instructions["texto"])}

INSTRUCCIONES ADICIONALES PARA EL ESTILO:
{style_adaptations.get(style, style_adaptations["photorealistic"])}

Por favor, responde ÚNICAMENTE con el prompt visual en inglés optimizado para Flux, sin explicaciones adicionales."""
        
        data = {
            "model": model,
            "max_tokens": 200,
            "temperature": 0.3,  # Menos temperatura para más consistencia
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            response_data = response.json()
            visual_prompt = response_data["content"][0]["text"].strip()
            return visual_prompt
        else:
            st.error(f"Error generando prompt visual con Claude: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error en la generación de prompt visual con Claude: {str(e)}")
        return None

# ===== INTERFAZ PRINCIPAL CON COLUMNAS CORREGIDAS =====
# Crear las columnas PRIMERO, antes de definir el contenido
col1, col2 = st.columns([2, 1])

# ===== COLUMNA DERECHA (col2) - MOVER ARRIBA PARA ALINEAR =====
with col2:
    st.header("🚀 Generación")
    
    # Información del modelo mejorada
    st.info(f"🧠 **Claude**: {claude_model}\n\n🎨 **Flux**: {flux_model}\n\n🗣️ **Voz**: {voice_model}")
    
    # Información sobre el sistema de prompts
    st.success("🔬 **Sistema Inteligente:**\n\nClaude analiza todo tu contenido para generar prompts visuales perfectamente adaptados")
    
    # Información sobre las nuevas tipologías
    with st.expander("🆕 Nuevas tipologías disponibles"):
        st.markdown("""
        **🗣️ Diálogos situacionales**: Conversaciones naturales (6-10 líneas)
        
        **🎭 Artículo cultural**: Tradiciones y costumbres (120-150 palabras)
        
        **📺 Artículo de actualidad**: Noticias simplificadas (80-120 palabras)
        
        **👤 Artículo biográfico**: Mini-biografías (100-120 palabras)
        
        **📱 Clip de noticias**: 5 noticias ultrabreves (40-60 palabras c/u)
        
        **💭 Pregunta de debate**: Dilemas para conversación (2-3 frases)
        
        **👨‍🍳 Receta de cocina**: Recetas sencillas (80-100 palabras)
        
        **📲 Post de redes sociales**: Contenido informal (40-60 palabras)
        
        **🧠 Trivia cultural**: 6 preguntas de cultura general
        """)
    
    # Botón principal
    generate_button = st.button(
        "🎯 Generar Contenido Multimedia",
        type="primary",
        use_container_width=True
    )
    
    # Validación de APIs
    apis_ready = all([anthropic_api_key, bfl_api_key, openai_api_key])
    if not apis_ready:
        missing_apis = []
        if not anthropic_api_key: missing_apis.append("Anthropic")
        if not bfl_api_key: missing_apis.append("Black Forest Labs")  
        if not openai_api_key: missing_apis.append("OpenAI")
        
        st.warning(f"⚠️ APIs faltantes: {', '.join(missing_apis)}")

# ===== COLUMNA IZQUIERDA (col1) - CONTENIDO PRINCIPAL =====
with col1:
    st.header("📝 Generación de Contenido")
    
    # Input del usuario con ejemplos ampliados
    user_prompt = st.text_area(
        "Describe tu idea:",
        placeholder="""Ejemplos por tipo de contenido:

🎓 Ejercicio: "Funciones lineales para estudiantes de secundaria"
📰 Artículo: "El futuro de la energía renovable" 
📚 Texto: "Guía de productividad personal"
📖 Relato: "Un gato que viaja en el tiempo"

🗣️ Diálogo situacional: "Pidiendo direcciones en el aeropuerto"
🎭 Artículo cultural: "La celebración del Día de Muertos en México"
📺 Artículo de actualidad: "Nuevas medidas ambientales aprobadas"
👤 Artículo biográfico: "Frida Kahlo, pintora mexicana"

📱 Clip de noticias: "Avances tecnológicos de esta semana"
💭 Pregunta de debate: "¿Es ético usar inteligencia artificial en educación?"
👨‍🍳 Receta de cocina: "Cómo hacer tacos al pastor auténticos"
📲 Post de redes sociales: "Consejos para ser más sostenible"
🧠 Trivia cultural: "Conocimientos sobre arte latinoamericano" """,
        height=150
    )
    
    # Tipo de contenido (AMPLIADO)
    content_type = st.selectbox(
        "Tipo de contenido a generar:",
        ["ejercicio", "artículo", "texto", "relato", "diálogo situacional", 
         "artículo cultural", "artículo de actualidad", "artículo biográfico", 
         "clip de noticias", "pregunta de debate", "receta de cocina", 
         "post de redes sociales", "trivia cultural"],
        help="Selecciona el tipo que mejor se adapte a tu necesidad"
    )
    
    # Prompt opcional para imagen
    st.subheader("🖼️ Personalización de Imagen (Opcional)")
    image_prompt = st.text_area(
        "Prompt personalizado para la imagen (en inglés):",
        placeholder="""Opcional: Describe específicamente qué imagen quieres generar EN INGLÉS.
Si lo dejas vacío, Claude analizará el contenido y generará automáticamente un prompt optimizado.

Ejemplos:
• A person studying with mathematics books in a modern library, natural lighting, photorealistic
• A futuristic landscape with solar panels and wind turbines at sunset, cinematic composition
• An orange cat wearing a steampunk hat traveling in a time machine, digital art style
• Two people having a conversation at an airport terminal, documentary style
• Traditional Day of the Dead altar with colorful decorations, cultural photography
• A modern newsroom with journalists working, professional lighting""",
        height=120,
        help="Si especificas un prompt EN INGLÉS, este se usará en lugar del generado automáticamente por Claude"
    )
# Función para optimizar prompt para Flux (ahora simplificada ya que Claude genera el prompt completo)
def optimize_prompt_for_flux(prompt, style="photorealistic"):
    """Aplica optimizaciones finales al prompt ya generado por Claude"""
    try:
        # Agregar términos técnicos finales si no están presentes
        quality_terms = "high quality, detailed, professional"
        resolution_terms = "8K resolution, sharp focus"
        
        # Verificar si ya contiene términos de calidad
        prompt_lower = prompt.lower()
        if not any(term in prompt_lower for term in ["high quality", "8k", "detailed", "professional", "masterpiece"]):
            prompt += f", {quality_terms}, {resolution_terms}"
        
        return prompt
    except Exception as e:
        st.error(f"Error optimizando prompt: {str(e)}")
        return prompt

# Función para generar imagen con Flux Pro (basada en el archivo de referencia)
def generate_image_flux_pro(prompt, width, height, steps, api_key):
    """Genera imagen usando Flux Pro 1.1"""
    headers = {
        'accept': 'application/json',
        'x-key': api_key,
        'Content-Type': 'application/json',
    }
    
    json_data = {
        'prompt': prompt,
        'width': int(width),
        'height': int(height),
        'steps': int(steps),
        'prompt_upsampling': False,
        'seed': 42,  # Seed fijo para consistencia
        'guidance': 2.5,
        'safety_tolerance': 2,
        'interval': 2,
        'output_format': 'jpeg'
    }
    
    response = requests.post(
        'https://api.bfl.ml/v1/flux-pro-1.1',
        headers=headers,
        json=json_data,
    )
    
    return process_flux_response(response, api_key)

# Función para generar imagen con Flux Ultra (basada en el archivo de referencia)  
def generate_image_flux_ultra(prompt, aspect_ratio, api_key):
    """Genera imagen usando Flux Pro 1.1 Ultra"""
    headers = {
        'accept': 'application/json',
        'x-key': api_key,
        'Content-Type': 'application/json',
    }
    
    json_data = {
        'prompt': prompt,
        'seed': 42,
        'aspect_ratio': aspect_ratio,
        'safety_tolerance': 2,
        'output_format': 'jpeg',
        'raw': False
    }
    
    response = requests.post(
        'https://api.bfl.ml/v1/flux-pro-1.1-ultra',
        headers=headers,
        json=json_data,
    )
    
    return process_flux_response(response, api_key)

# Función para procesar respuesta de Flux (basada en el archivo de referencia)
def process_flux_response(response, api_key):
    """Procesa la respuesta de Flux y hace polling hasta obtener la imagen"""
    if response.status_code != 200:
        return f"Error: {response.status_code} {response.text}"
    
    request = response.json()
    request_id = request.get("id")
    if not request_id:
        return "No se pudo obtener el ID de la solicitud."

    with st.spinner('Generando imagen con Flux...'):
        max_attempts = 60  # 5 minutos máximo
        for attempt in range(max_attempts):
            time.sleep(5)  # Esperar 5 segundos entre consultas
            
            result_response = requests.get(
                'https://api.bfl.ml/v1/get_result',
                headers={
                    'accept': 'application/json',
                    'x-key': api_key,
                },
                params={
                    'id': request_id,
                },
            )
            
            if result_response.status_code != 200:
                return f"Error: {result_response.status_code} {result_response.text}"
            
            result = result_response.json()
            status = result.get("status")
            
            if status == "Ready":
                image_url = result['result'].get('sample')
                if not image_url:
                    return "No se encontró URL de imagen en el resultado."
                
                image_response = requests.get(image_url)
                if image_response.status_code != 200:
                    return f"Error al obtener la imagen: {image_response.status_code}"
                
                image = Image.open(BytesIO(image_response.content))
                jpg_image = image.convert("RGB")
                return jpg_image
                
            elif status == "Failed":
                return "La generación de la imagen falló."
            elif status == "Pending":
                # Mostrar progreso
                st.info(f"Procesando... Intento {attempt + 1}/{max_attempts}")
                pass
            else:
                return f"Estado inesperado: {status}"
        
        return "Timeout: La generación tomó demasiado tiempo."

# Función principal para generar imagen con Flux (MEJORADA)
def generate_image_flux(text_content: str, content_type: str, api_key: str, model: str, width: int, height: int, steps: int, style: str = "photorealistic", custom_prompt: str = None, claude_api_key: str = None, claude_model: str = None) -> tuple[Optional[Image.Image], str]:
    """Genera imagen usando Flux con prompt inteligente generado por Claude"""
    try:
        # Determinar qué prompt usar
        if custom_prompt and custom_prompt.strip():
            # Usar el prompt personalizado del usuario (ya en inglés)
            visual_prompt = custom_prompt.strip()
            final_prompt = optimize_prompt_for_flux(visual_prompt, style)
            st.info(f"🎨 Usando prompt personalizado para la imagen")
            prompt_source = "personalizado"
        else:
            # Generar prompt automáticamente usando Claude
            st.info(f"🤖 Analizando contenido con Claude para generar prompt visual...")
            
            if not claude_api_key:
                # Fallback al método anterior si no hay API de Claude
                content_preview = ' '.join(text_content.split()[:80])
                visual_prompt = f"A realistic scene representing: {content_preview}. Real world setting, natural environment, authentic details"
                st.warning("⚠️ Usando método básico (falta Claude API key para análisis inteligente)")
                prompt_source = "básico"
            else:
                # Usar Claude para generar prompt inteligente
                visual_prompt = generate_visual_prompt_with_claude(
                    text_content, content_type, style, claude_api_key, claude_model
                )
                
                if visual_prompt:
                    st.success(f"✅ Claude analizó el {content_type} y generó prompt visual optimizado")
                    prompt_source = "inteligente"
                else:
                    # Fallback si Claude falla
                    content_preview = ' '.join(text_content.split()[:80])
                    visual_prompt = f"A realistic scene representing: {content_preview}. Real world setting, natural environment, authentic details"
                    st.warning("⚠️ Usando método básico (error en análisis de Claude)")
                    prompt_source = "básico"
            
            final_prompt = optimize_prompt_for_flux(visual_prompt, style)
        
        # Mostrar información del prompt generado
        with st.expander(f"📝 Prompt generado ({prompt_source})"):
            st.code(final_prompt, language="text")
            if prompt_source == "inteligente":
                st.success("🧠 Prompt generado por Claude analizando todo el contenido")
            elif prompt_source == "personalizado":
                st.info("👤 Prompt personalizado proporcionado por el usuario")
            else:
                st.warning("⚙️ Prompt básico (primeras palabras del contenido)")
        
        # Generar imagen según el modelo
        if model == "flux-pro-1.1-ultra":
            # Usar Ultra con aspect ratio
            aspect_ratio = f"{width}:{height}" if width == height else "16:9"
            result = generate_image_flux_ultra(final_prompt, aspect_ratio, api_key)
        else:
            # Usar Pro normal
            result = generate_image_flux_pro(final_prompt, width, height, steps, api_key)
        
        if isinstance(result, Image.Image):
            return result, final_prompt
        else:
            st.error(f"Error en Flux: {result}")
            return None, final_prompt
            
    except Exception as e:
        st.error(f"Error en la generación de imagen con Flux: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None, ""

# Función para generar audio con OpenAI TTS (mantenemos la misma)
def generate_audio(text: str, voice: str, api_key: str) -> Optional[bytes]:
    """Genera audio usando OpenAI Text-to-Speech"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Limpiar y preparar el texto para TTS
        clean_text = text.replace('\n\n', '. ').replace('\n', ' ').strip()
        if len(clean_text) > 4000:
            clean_text = clean_text[:4000] + "..."
        
        data = {
            "model": "tts-1-hd",  # Usar el modelo HD para mejor calidad
            "input": clean_text,
            "voice": voice,
            "response_format": "mp3"
        }
        
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Error generando audio: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error en la generación de audio: {str(e)}")
        return None

# ===== PROCESO DE GENERACIÓN (MEJORADO) =====
if generate_button and user_prompt:
    if not apis_ready:
        st.error("❌ Por favor, proporciona todas las claves de API necesarias.")
    else:
        # Limpiar contenido anterior
        st.session_state.generated_content = {}
        st.session_state.generation_complete = False
        
        # Progress bar mejorada
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Paso 1: Generar texto con Claude Sonnet 4
            status_text.text(f"🧠 Generando {content_type} con Claude Sonnet 4...")
            progress_bar.progress(15)
            
            generated_text = generate_text_claude(
                user_prompt, content_type, anthropic_api_key, 
                claude_model, max_tokens_claude
            )
            
            if generated_text:
                # Guardar en session state
                st.session_state.generated_content['text'] = generated_text
                st.session_state.generated_content['text_metadata'] = {
                    'word_count': len(generated_text.split()),
                    'char_count': len(generated_text),
                    'content_type': content_type,
                    'timestamp': int(time.time())
                }
                
                progress_bar.progress(30)
                
                # Paso 2: Generar imagen con Flux (MEJORADO)
                status_text.text(f"🎨 Analizando {content_type} y generando imagen con Flux...")
                progress_bar.progress(40)
                
                generated_image, used_prompt = generate_image_flux(
                    generated_text, content_type, bfl_api_key, flux_model,
                    image_width, image_height, flux_steps, image_style, 
                    image_prompt, anthropic_api_key, claude_model
                )
                
                if generated_image:
                    # Guardar imagen en session state con información del prompt
                    img_buffer = io.BytesIO()
                    generated_image.save(img_buffer, format="PNG", quality=95)
                    img_bytes = img_buffer.getvalue()
                    
                    st.session_state.generated_content['image'] = img_bytes
                    st.session_state.generated_content['image_obj'] = generated_image
                    st.session_state.generated_content['image_metadata'] = {
                        'width': image_width,
                        'height': image_height,
                        'model': flux_model,
                        'steps': flux_steps,
                        'style': image_style,
                        'custom_prompt': bool(image_prompt and image_prompt.strip()),
                        'used_prompt': used_prompt,
                        'prompt_intelligent': not bool(image_prompt and image_prompt.strip()),
                        'timestamp': int(time.time())
                    }
                
                progress_bar.progress(70)
                
                # Paso 3: Generar audio
                status_text.text("🗣️ Generando narración en audio...")
                progress_bar.progress(85)
                
                generated_audio = generate_audio(generated_text, voice_model, openai_api_key)
                
                if generated_audio:
                    # Guardar audio en session state
                    st.session_state.generated_content['audio'] = generated_audio
                    st.session_state.generated_content['audio_metadata'] = {
                        'voice': voice_model,
                        'size_kb': len(generated_audio) / 1024,
                        'timestamp': int(time.time())
                    }
                
                # Marcar como completado
                st.session_state.generation_complete = True
                
                # Completado
                progress_bar.progress(100)
                status_text.text("✅ ¡Contenido multimedia generado exitosamente!")
                
                # Balloons solo una vez
                st.balloons()
                st.success("🎉 **¡Generación completada!** Tu contenido multimedia está listo.")
                
            else:
                st.error("❌ Error al generar el contenido de texto con Claude.")
                
        except Exception as e:
            st.error(f"❌ Error durante la generación: {str(e)}")
            progress_bar.progress(0)
            status_text.text("❌ Generación fallida")

# ===== MOSTRAR CONTENIDO GENERADO DESDE SESSION STATE (MEJORADO) =====
if st.session_state.generation_complete and st.session_state.generated_content:
    # Contenedores para resultados
    text_container = st.container()
    image_container = st.container()
    audio_container = st.container()
    
    # Mostrar texto (MEJORADO para nuevas tipologías)
    if 'text' in st.session_state.generated_content:
        with text_container:
            metadata = st.session_state.generated_content.get('text_metadata', {})
            content_type_display = metadata.get('content_type', 'texto')
            
            # Emojis por tipo de contenido
            content_emojis = {
                "ejercicio": "📚", "artículo": "📰", "texto": "📝", "relato": "📖",
                "diálogo situacional": "🗣️", "artículo cultural": "🎭", 
                "artículo de actualidad": "📺", "artículo biográfico": "👤",
                "clip de noticias": "📱", "pregunta de debate": "💭",
                "receta de cocina": "👨‍🍳", "post de redes sociales": "📲",
                "trivia cultural": "🧠"
            }
            
            emoji = content_emojis.get(content_type_display, "📄")
            st.header(f"{emoji} {content_type_display.title()} Generado por Claude")
            
            st.markdown(st.session_state.generated_content['text'])
            
            # Métricas del texto
            word_count = metadata.get('word_count', 0)
            char_count = metadata.get('char_count', 0)
            
            # Información específica por tipo
            type_info = {
                "diálogo situacional": f"Conversación de {word_count} palabras con expresiones clave",
                "artículo cultural": f"Artículo cultural de {word_count} palabras con glosario",
                "artículo de actualidad": f"Noticia simplificada de {word_count} palabras con preguntas",
                "artículo biográfico": f"Biografía de {word_count} palabras con dato curioso",
                "clip de noticias": f"5 clips de noticias en {word_count} palabras total",
                "pregunta de debate": f"Pregunta de debate en {word_count} palabras",
                "receta de cocina": f"Receta de {word_count} palabras con ingredientes y pasos",
                "post de redes sociales": f"Post de {word_count} palabras con emojis y hashtags",
                "trivia cultural": f"6 preguntas de trivia con {word_count} palabras"
            }
            
            display_info = type_info.get(content_type_display, f"📊 {word_count} palabras • {char_count} caracteres")
            st.caption(display_info)
            
            # Botón para descargar texto con key única
            text_timestamp = metadata.get('timestamp', int(time.time()))
            st.download_button(
                label="📥 Descargar Texto",
                data=st.session_state.generated_content['text'],
                file_name=f"{content_type_display.replace(' ', '_')}_claude_{text_timestamp}.txt",
                mime="text/plain",
                key=f"download_text_{text_timestamp}"
            )
    
    # Mostrar imagen (MEJORADO)
    if 'image_obj' in st.session_state.generated_content:
        with image_container:
            st.header("🖼️ Imagen Generada por Flux")
            
            metadata = st.session_state.generated_content.get('image_metadata', {})
            width = metadata.get('width', 'N/A')
            height = metadata.get('height', 'N/A')
            model = metadata.get('model', 'N/A')
            style = metadata.get('style', 'N/A')
            custom_prompt_used = metadata.get('custom_prompt', False)
            intelligent_prompt = metadata.get('prompt_intelligent', False)
            used_prompt = metadata.get('used_prompt', '')
            
            # Descripción mejorada con información del tipo de prompt
            if custom_prompt_used:
                prompt_info = "Con prompt personalizado"
                prompt_color = "🟢"
            elif intelligent_prompt:
                prompt_info = "Prompt inteligente por Claude"
                prompt_color = "🔵"
            else:
                prompt_info = "Prompt básico automático"
                prompt_color = "🟡"
            
            caption = f"Generada con {model} • {width}x{height}px • Estilo: {style} • {prompt_color} {prompt_info}"
            
            st.image(
                st.session_state.generated_content['image_obj'], 
                caption=caption
            )
            
            # Información del prompt usado
            with st.expander("🔍 Ver prompt utilizado para la imagen"):
                st.code(used_prompt, language="text")
                if intelligent_prompt:
                    st.success("🧠 Este prompt fue generado por Claude analizando todo el contenido del texto")
                elif custom_prompt_used:
                    st.info("👤 Este fue tu prompt personalizado")
                else:
                    st.warning("⚙️ Prompt básico generado automáticamente")
            
            # Información adicional
            if custom_prompt_used:
                st.success("✨ Se utilizó tu prompt personalizado para la imagen")
            elif intelligent_prompt:
                st.success("🤖 Claude analizó el contenido completo para generar un prompt visual optimizado")
            else:
                st.info("⚙️ Se usó el método básico de generación de prompt")
            
            # Botón para descargar imagen con key única
            img_timestamp = metadata.get('timestamp', int(time.time()))
            st.download_button(
                label="📥 Descargar Imagen",
                data=st.session_state.generated_content['image'],
                file_name=f"flux_image_{img_timestamp}.png",
                mime="image/png",
                key=f"download_image_{img_timestamp}"
            )
    
    # Mostrar audio
    if 'audio' in st.session_state.generated_content:
        with audio_container:
            st.header("🎵 Audio Generado")
            st.audio(st.session_state.generated_content['audio'], format="audio/mp3")
            
            # Información del audio
            metadata = st.session_state.generated_content.get('audio_metadata', {})
            voice = metadata.get('voice', 'N/A')
            size_kb = metadata.get('size_kb', 0)
            
            st.caption(f"🎧 Voz: {voice} • Tamaño: {size_kb:.1f} KB")
            
            # Botón para descargar audio con key única
            audio_timestamp = metadata.get('timestamp', int(time.time()))
            st.download_button(
                label="📥 Descargar Audio",
                data=st.session_state.generated_content['audio'],
                file_name=f"audio_tts_{audio_timestamp}.mp3",
                mime="audio/mp3",
                key=f"download_audio_{audio_timestamp}"
            )
    
    # Estadísticas finales (MEJORADAS)
    with st.expander("📈 Estadísticas de generación"):
        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        
        text_meta = st.session_state.generated_content.get('text_metadata', {})
        image_meta = st.session_state.generated_content.get('image_metadata', {})
        
        with col_stats1:
            st.metric("Palabras generadas", text_meta.get('word_count', 0))
        with col_stats2:
            width = image_meta.get('width', 0)
            height = image_meta.get('height', 0)
            st.metric("Resolución imagen", f"{width}x{height}" if width and height else "N/A")
        with col_stats3:
            st.metric("Pasos Flux", image_meta.get('steps', 0))
        with col_stats4:
            content_type = text_meta.get('content_type', 'texto')
            st.metric("Tipo contenido", content_type.title())
    
    # Botón para limpiar y empezar de nuevo
    if st.button("🔄 Generar Nuevo Contenido", type="secondary"):
        st.session_state.generated_content = {}
        st.session_state.generation_complete = False
        st.rerun()

# ===== INFORMACIÓN ADICIONAL EN EL FOOTER =====
st.markdown("---")

# Tabs informativas (ACTUALIZADAS CON NUEVAS TIPOLOGÍAS)
tab1, tab2, tab3, tab4 = st.tabs(["📚 Instrucciones", "🔑 APIs", "💡 Consejos", "⚡ Modelos"])

with tab1:
    st.markdown("""
    ### Cómo usar la aplicación:
    
    1. **🔧 Configura las APIs**: Ingresa tus claves en la barra lateral
    2. **✏️ Escribe tu prompt**: Describe detalladamente qué quieres generar  
    3. **📋 Selecciona el tipo**: Ahora con **13 tipologías** diferentes disponibles
    4. **⚙️ Personaliza**: Ajusta modelos y configuraciones según tus necesidades
    5. **🚀 Genera**: Presiona el botón y espera tu contenido multimedia completo
    
    ### 🆕 **Nuevas tipologías añadidas:**
    
    **🗣️ Diálogos situacionales**: Conversaciones naturales en contextos específicos
    
    **🎭 Artículo cultural**: Tradiciones, costumbres y elementos culturales
    
    **📺 Artículo de actualidad**: Noticias adaptadas y simplificadas
    
    **👤 Artículo biográfico**: Mini-biografías con datos curiosos
    
    **📱 Clip de noticias**: 5 noticias ultrabreves estilo teletipo
    
    **💭 Pregunta de debate**: Dilemas para estimular conversación
    
    **👨‍🍳 Receta de cocina**: Recetas paso a paso con ingredientes
    
    **📲 Post de redes sociales**: Contenido informal con emojis y hashtags
    
    **🧠 Trivia cultural**: Preguntas de cultura general con explicaciones
    """)

with tab2:
    st.markdown("""
    ### APIs necesarias:
    
    **🧠 Anthropic API (Claude)**
    - Regístrate en: https://console.anthropic.com/
    - Crea una API key en tu dashboard
    - Usado para: Generación de todas las tipologías de texto + Análisis para prompts visuales
    
    **🎨 Black Forest Labs API (Flux)**
    - Regístrate en: https://api.bfl.ml/
    - Obtén tu API key del panel de control  
    - Usado para generación de imágenes adaptadas a cada tipo de contenido
    
    **🗣️ OpenAI API (TTS)**
    - Regístrate en: https://platform.openai.com/
    - Crea una API key en tu cuenta
    - Usado para conversión de texto a voz (funciona con todas las tipologías)
    """)

with tab3:
    st.markdown("""
    ### Consejos para mejores resultados:
    
    **📝 Para el texto:**
    - **Sé específico** según la tipología elegida
    - **Ejemplos por tipo:**
      - Diálogos: "Pidiendo direcciones en el aeropuerto de Madrid"
      - Cultural: "La tradición del flamenco en Andalucía"
      - Recetas: "Cómo hacer gazpacho andaluz tradicional"
      - Trivia: "Preguntas sobre arte latinoamericano contemporáneo"
    
    **🖼️ Para las imágenes:**
    - **🤖 Automático Inteligente (RECOMENDADO)**: Claude adapta el análisis visual a cada tipología
    - **Ejemplos de adaptación automática:**
      - Diálogos → Escenas de conversación natural
      - Recetas → Ingredientes y cocina acogedora  
      - Cultural → Elementos tradicionales y costumbres
      - Trivia → Ambiente educativo y cultural
    - **👤 Personalizado**: Escribe tu prompt EN INGLÉS para control total
    
    **🎵 Para el audio:**
    - Funciona igual de bien con todas las tipologías
    - Los textos breves (posts, clips) suenan especialmente naturales
    - Los diálogos se narran de forma fluida
    """)

with tab4:
    st.markdown("""
    ### Información de los modelos:
    
    **🧠 Claude Sonnet 4 (2025)**
    - Modelo más avanzado de Anthropic
    - claude-sonnet-4-20250514: La versión más reciente
    - Ahora especializado en **13 tipologías diferentes** de contenido
    - Doble función: Generación de texto + Análisis inteligente para prompts visuales
    
    **🎨 Flux (Black Forest Labs)**
    - **Flux Pro 1.1**: Control total de dimensiones, excelente calidad
    - **Flux Pro 1.1 Ultra**: Máxima calidad, aspect ratios automáticos
    - Optimizado para recibir prompts en inglés
    - Adaptación automática según tipología de contenido
    
    **🗣️ OpenAI TTS-1-HD**
    - Modelo de alta definición para síntesis de voz
    - 6 voces diferentes con personalidades únicas
    - Funciona perfectamente con todas las tipologías
    - Calidad de audio profesional
    
    ### 🆕 **Mejoras en esta versión:**
    
    **📋 13 Tipologías de Contenido:**
    - Originales: Ejercicio, Artículo, Texto, Relato
    - Nuevas: Diálogo situacional, Artículo cultural, Artículo de actualidad, Artículo biográfico, Clip de noticias, Pregunta de debate, Receta de cocina, Post de redes sociales, Trivia cultural
    
    **🧠 Sistema de Prompts Inteligente Especializado:**
    - Análisis específico para cada tipo de contenido
    - Prompts visuales adaptados automáticamente
    - Mejor coherencia entre texto e imagen
    - Generación en inglés optimizada para Flux
    
    **🔧 Interfaz Mejorada:**
    - ✅ **Alineación perfecta de columnas**
    - Información organizada y clara
    - Feedback detallado en tiempo real
    - Estadísticas específicas por tipología
    """)
