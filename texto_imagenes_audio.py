import streamlit as st
import requests
import base64
import io
import time
from PIL import Image
from io import BytesIO
import json
import os
import hashlib
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

# NUEVO: Session state para secuencias de personajes
if 'character_sequence_mode' not in st.session_state:
    st.session_state.character_sequence_mode = False

if 'character_analysis' not in st.session_state:
    st.session_state.character_analysis = None

if 'character_images' not in st.session_state:
    st.session_state.character_images = []

if 'sequence_generation_complete' not in st.session_state:
    st.session_state.sequence_generation_complete = False

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
    
    # NUEVO: Configuración para secuencias de personajes
    st.subheader("🎭 Secuencias de Personajes")
    sequence_mode = st.checkbox(
        "Activar modo secuencia",
        value=st.session_state.character_sequence_mode,
        help="Genera múltiples imágenes con los mismos personajes"
    )
    
    if sequence_mode != st.session_state.character_sequence_mode:
        st.session_state.character_sequence_mode = sequence_mode
        # Limpiar datos anteriores si se cambia el modo
        if not sequence_mode:
            st.session_state.character_analysis = None
            st.session_state.character_images = []
            st.session_state.sequence_generation_complete = False
        st.rerun()
    
    # Configuraciones específicas según modelo de Flux
    if flux_model == "flux-pro-1.1":
        image_width = st.selectbox("Ancho de imagen", [512, 768, 1024, 1344], index=2)
        image_height = st.selectbox("Alto de imagen", [512, 768, 1024, 1344], index=2)
    else:  # Ultra
        st.info("💡 Flux Ultra maneja las dimensiones automáticamente")
        image_width = 1024  # Valor por defecto para Ultra
        image_height = 1024

# ===============================
# FUNCIONES PARA DETECCIÓN DE PERSONAJES
# ===============================

def analyze_characters_with_claude(text_content: str, content_type: str, api_key: str, model: str) -> Dict[str, Any]:
    """Analiza el texto con Claude para detectar personajes y generar character cards con escenas específicas y variadas"""
    try:
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        system_prompt = """Eres un experto en análisis narrativo y dirección visual cinematográfica. Tu tarea es analizar texto narrativo y extraer información detallada sobre personajes para generar secuencias de imágenes visualmente variadas pero consistentes.

INSTRUCCIONES CLAVE:
1. Identifica TODOS los personajes principales con características físicas específicas
2. Analiza el relato MOMENTO A MOMENTO para extraer escenas clave
3. Para cada escena, genera una descripción visual ÚNICA con diferentes:
   - Ángulos de cámara (close-up, wide shot, medium shot, etc.)
   - Emociones y expresiones específicas del momento
   - Composición visual (primer plano, plano general, etc.)
   - Iluminación y ambiente según la narrativa
   - Poses y acciones específicas del personaje

FORMATO DE RESPUESTA (JSON válido):
{
  "has_characters": true/false,
  "characters": [
    {
      "name": "nombre_descriptivo",
      "type": "human/animal/creature",
      "physical_description": "descripción física DETALLADA en inglés (color específico, características únicas, tamaño, etc.)",
      "key_features": ["característica física específica 1", "característica física específica 2", "característica física específica 3"],
      "suggested_scenes": [
        {
          "action": "momento específico del relato",
          "scene_description": "descripción visual COMPLETA en inglés incluyendo: [PERSONAJE con características físicas], [ACCIÓN específica], [EMOCIÓN visible], [COMPOSICIÓN de cámara], [AMBIENTE/ILUMINACIÓN], [ELEMENTOS del entorno]",
          "visual_composition": "tipo de plano (close-up/medium/wide shot)",
          "emotional_state": "estado emocional específico del personaje",
          "lighting_mood": "tipo de iluminación apropiada"
        }
      ]
    }
  ],
  "visual_style": "estilo visual sugerido",
  "consistency_notes": "elementos clave para mantener consistencia visual entre escenas"
}

EJEMPLOS DE SCENE_DESCRIPTION VARIADAS:
- "Luna, white hen with bright red comb and small black eyes, looking desperately worried in close-up, searching frantically around empty wooden chicken coop, morning sunlight casting long shadows"
- "Luna, white hen with bright red comb and small black eyes, in medium shot talking emotionally to pink pig Max near rustic wooden fence, tears visible in eyes, soft golden afternoon light"
- "Luna, white hen with bright red comb and small black eyes, wide shot walking courageously through dark mysterious forest with pink pig companion, dramatic low-angle view, filtered sunlight through trees"

IMPORTANTE: Cada scene_description debe ser VISUALMENTE DISTINTA con diferentes composiciones, ángulos y ambientes."""

        user_message = f"""Analiza el siguiente {content_type} momento a momento y extrae información detallada sobre personajes:

CONTENIDO COMPLETO:
{text_content}

INSTRUCCIONES ESPECÍFICAS:
1. Lee todo el relato/cuento completo
2. Identifica los momentos narrativos clave donde cada personaje tiene una acción/emoción específica
3. Para cada momento, crea una escena visualmente ÚNICA con descripción completa
4. Asegúrate de que cada scene_description tenga:
   - Características físicas específicas del personaje
   - Acción/pose diferente
   - Emoción visible apropiada al momento
   - Composición de cámara variada
   - Ambiente/iluminación acorde a la narrativa

OBJETIVO: Generar 3-5 escenas por personaje que cuenten la historia visualmente con MÁXIMA VARIEDAD pero manteniendo la consistencia del personaje.

Responde ÚNICAMENTE con el JSON solicitado."""

        data = {
            "model": model,
            "max_tokens": 3000,  # Aumentado para análisis más detallado
            "temperature": 0.4,  # Ligeramente más creativo
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=90
        )
        
        if response.status_code == 200:
            response_data = response.json()
            claude_response = response_data["content"][0]["text"].strip()
            
            # Limpiar respuesta de Claude (quitar markdown si existe)
            if claude_response.startswith("```json"):
                claude_response = claude_response.replace("```json", "").replace("```", "").strip()
            
            # Parsear JSON
            try:
                character_data = json.loads(claude_response)
                
                # Validar que se generaron escenas variadas
                if character_data.get("has_characters", False):
                    total_scenes = sum(len(char.get("suggested_scenes", [])) for char in character_data.get("characters", []))
                    if total_scenes > 0:
                        st.success(f"✅ Claude generó {total_scenes} escenas variadas para la secuencia")
                
                return character_data
            except json.JSONDecodeError as e:
                st.error(f"Error parseando análisis de personajes: {e}")
                st.error(f"Respuesta de Claude: {claude_response[:500]}...")
                return {"has_characters": False, "characters": []}
        else:
            st.error(f"Error en análisis de personajes: {response.status_code}")
            return {"has_characters": False, "characters": []}
            
    except Exception as e:
        st.error(f"Error analizando personajes: {str(e)}")
        return {"has_characters": False, "characters": []}

def generate_character_seed(character_name: str, scene_action: str = "") -> int:
    """
    Genera un seed consistente basado en el personaje con variación controlada por escena
    
    Args:
        character_name: Nombre del personaje (para consistencia base)
        scene_action: Acción específica de la escena (para variación)
    
    Returns:
        Seed que mantiene consistencia del personaje pero permite variación visual
    """
    import hashlib
    
    # Seed base del personaje (siempre igual para el mismo personaje)
    base_hash = hashlib.md5(character_name.encode()).hexdigest()
    base_seed = int(base_hash[:6], 16) % 50000
    
    # Variación sutil por escena (si se proporciona)
    if scene_action and scene_action.strip():
        scene_hash = hashlib.md5(scene_action.encode()).hexdigest()
        scene_variation = int(scene_hash[:3], 16) % 1000
        
        # Combinar: mantener consistencia del personaje + añadir variación de escena
        final_seed = base_seed + scene_variation
    else:
        # Si no hay acción específica, usar solo el seed base del personaje
        final_seed = base_seed
    
    # Asegurar que el seed esté en rango válido
    return final_seed % 100000

def create_character_prompt(character: Dict, scene: Dict, style: str = "photorealistic") -> str:
    """Crea un prompt optimizado para Flux combinando personaje + escena"""
    base_character = character["physical_description"]
    scene_description = scene["scene_description"]
    
    # Plantilla base para prompts consistentes
    prompt_template = f"{base_character}, {scene_description}"
    
    # Añadir estilo y calidad
    style_suffix = {
        "photorealistic": "photorealistic, high quality, detailed, professional photography",
        "digital-art": "digital art, high quality, artistic, professional illustration",
        "cinematic": "cinematic composition, dramatic lighting, film photography",
        "documentary": "documentary style, natural lighting, authentic photography",
        "portrait": "portrait photography, professional lighting, high quality"
    }
    
    final_prompt = f"{prompt_template}, {style_suffix.get(style, style_suffix['photorealistic'])}"
    
    return final_prompt
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
def generate_image_flux_pro(prompt, width, height, steps, api_key, seed=None):
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
        'seed': seed if seed is not None else 42,  # Usar seed proporcionado o default
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
def generate_image_flux_ultra(prompt, aspect_ratio, api_key, seed=None):
    """Genera imagen usando Flux Pro 1.1 Ultra"""
    headers = {
        'accept': 'application/json',
        'x-key': api_key,
        'Content-Type': 'application/json',
    }
    
    json_data = {
        'prompt': prompt,
        'seed': seed if seed is not None else 42,  # Usar seed proporcionado o default
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
# Función principal para generar imagen con Flux (MEJORADA CON SOPORTE PARA SECUENCIAS)
def generate_image_flux(text_content: str, content_type: str, api_key: str, model: str, width: int, height: int, steps: int, style: str = "photorealistic", custom_prompt: str = None, claude_api_key: str = None, claude_model: str = None, character_seed: int = None) -> tuple[Optional[Image.Image], str]:
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
        with st.expander(f"🔍 Prompt generado ({prompt_source})"):
            st.code(final_prompt, language="text")
            if prompt_source == "inteligente":
                st.success("🧠 Prompt generado por Claude analizando todo el contenido")
            elif prompt_source == "personalizado":
                st.info("👤 Prompt personalizado proporcionado por el usuario")
            else:
                st.warning("⚙️ Prompt básico (primeras palabras del contenido)")
        
        # Generar imagen según el modelo con seed opcional
        if model == "flux-pro-1.1-ultra":
            # Usar Ultra con aspect ratio
            aspect_ratio = f"{width}:{height}" if width == height else "16:9"
            result = generate_image_flux_ultra(final_prompt, aspect_ratio, api_key, character_seed)
        else:
            # Usar Pro normal
            result = generate_image_flux_pro(final_prompt, width, height, steps, api_key, character_seed)
        
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

# NUEVA FUNCIÓN: Generar secuencia de imágenes con personajes consistentes
def generate_character_sequence(text_content: str, content_type: str, character_analysis: Dict[str, Any], flux_config: Dict[str, Any]) -> Dict[str, Any]:
    """Genera múltiples imágenes con personajes consistentes usando seeds variables por escena"""
    
    sequence_results = {
        "success": True,
        "character_cards": [],
        "total_images": 0,
        "errors": []
    }
    
    st.info("🎭 Iniciando generación de secuencia de personajes...")
    
    # Crear progress bar para toda la secuencia
    total_scenes = sum(len(char["suggested_scenes"]) for char in character_analysis["characters"])
    progress_bar = st.progress(0)
    scene_counter = 0
    
    for i, character in enumerate(character_analysis["characters"]):
        st.subheader(f"👤 Personaje {i+1}: {character['name']}")
        
        # Generar seed base para este personaje (sin escena específica)
        base_character_seed = generate_character_seed(character["name"])
        
        # Información del personaje
        with st.expander(f"📋 Character Card: {character['name']}"):
            st.write(f"**Tipo:** {character['type']}")
            st.write(f"**Descripción:** {character['physical_description']}")
            st.write(f"**Características clave:** {', '.join(character['key_features'])}")
            st.write(f"**Seed base:** {base_character_seed}")
        
        character_card = {
            "name": character["name"],
            "type": character["type"],
            "description": character["physical_description"],
            "seed": base_character_seed,  # Seed base para referencia
            "images": []
        }
        
        # Generar imagen para cada escena del personaje
        for j, scene in enumerate(character["suggested_scenes"]):
            scene_counter += 1
            progress_bar.progress(scene_counter / total_scenes)
            
            st.write(f"🎬 Escena {j+1}: {scene['action']}")
            
            # Generar seed específico para esta escena
            character_seed = generate_character_seed(character["name"])
            
            # Crear prompt específico para esta escena
            scene_prompt = create_character_prompt(character, scene, flux_config["style"])
            
            # Mostrar el prompt que se va a usar
            with st.expander(f"📝 Prompt para {scene['action']} (Seed: {character_seed})"):
                st.code(scene_prompt, language="text")
            
            # Generar imagen con seed específico de la escena
            try:
                if flux_config["model"] == "flux-pro-1.1-ultra":
                    aspect_ratio = f"{flux_config['width']}:{flux_config['height']}" if flux_config['width'] == flux_config['height'] else "16:9"
                    image_result = generate_image_flux_ultra(scene_prompt, aspect_ratio, flux_config["api_key"], character_seed)
                else:
                    image_result = generate_image_flux_pro(
                        scene_prompt, 
                        flux_config["width"], 
                        flux_config["height"], 
                        flux_config["steps"], 
                        flux_config["api_key"], 
                        character_seed
                    )
                
                if isinstance(image_result, Image.Image):
                    # Guardar imagen en session state
                    img_buffer = io.BytesIO()
                    image_result.save(img_buffer, format="PNG", quality=95)
                    img_bytes = img_buffer.getvalue()
                    
                    # Metadata de la imagen
                    image_data = {
                        "scene": scene["action"],
                        "prompt": scene_prompt,
                        "seed": character_seed,  # Usar el seed específico de la escena
                        "image_bytes": img_bytes,
                        "image_obj": image_result,
                        "timestamp": int(time.time()),
                        "character_name": character["name"]
                    }
                    
                    character_card["images"].append(image_data)
                    sequence_results["total_images"] += 1
                    
                    # Mostrar imagen generada
                    st.image(image_result, caption=f"{character['name']} - {scene['action']}")
                    st.success(f"✅ Imagen generada con seed {character_seed}")
                    
                else:
                    error_msg = f"Error generando imagen para {character['name']} - {scene['action']}: {image_result}"
                    st.error(error_msg)
                    sequence_results["errors"].append(error_msg)
                    
            except Exception as e:
                error_msg = f"Excepción generando imagen para {character['name']} - {scene['action']}: {str(e)}"
                st.error(error_msg)
                sequence_results["errors"].append(error_msg)
        
        sequence_results["character_cards"].append(character_card)
    
    progress_bar.progress(1.0)
    
    if sequence_results["total_images"] > 0:
        st.success(f"🎉 Secuencia completada: {sequence_results['total_images']} imágenes generadas")
        
        # Mostrar resumen por personaje
        for card in sequence_results["character_cards"]:
            if card["images"]:
                st.write(f"**{card['name']}**: {len(card['images'])} imágenes con seed {card['seed']}")
    else:
        st.error("❌ No se pudo generar ninguna imagen de la secuencia")
        sequence_results["success"] = False
    
    return sequence_results

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
    
    # NUEVO: Información sobre secuencias de personajes
    if st.session_state.character_sequence_mode:
        st.warning("🎭 **Modo Secuencia Activo:**\n\nSe generarán múltiples imágenes con personajes consistentes usando seeds fijos")
        
        # Mostrar análisis de personajes si existe
        if st.session_state.character_analysis:
            with st.expander("👥 Personajes detectados"):
                for i, char in enumerate(st.session_state.character_analysis.get("characters", [])):
                    st.write(f"**{i+1}. {char['name']}** ({char['type']})")
                    st.caption(f"Escenas: {len(char.get('suggested_scenes', []))}")
    
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
    
    # NUEVO: Botón para modo secuencia
    if st.session_state.character_sequence_mode:
        generate_sequence_button = st.button(
            "🎬 Generar Solo Secuencia de Imágenes",
            type="secondary",
            use_container_width=True,
            help="Genera solo las imágenes de personajes (requiere texto ya generado)"
        )
    else:
        generate_sequence_button = False
    
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

# ===== PROCESO DE GENERACIÓN PRINCIPAL (MEJORADO CON SOPORTE PARA SECUENCIAS) =====
if generate_button and user_prompt:
    if not apis_ready:
        st.error("⚠ Por favor, proporciona todas las claves de API necesarias.")
    else:
        # Limpiar contenido anterior
        st.session_state.generated_content = {}
        st.session_state.generation_complete = False
        st.session_state.character_analysis = None
        st.session_state.character_images = []
        st.session_state.sequence_generation_complete = False
        
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
                
                # Paso 1.5: NUEVO - Análisis de personajes si está en modo secuencia
                if st.session_state.character_sequence_mode:
                    status_text.text("🎭 Analizando personajes para secuencia...")
                    progress_bar.progress(35)
                    
                    character_analysis = analyze_characters_with_claude(
                        generated_text, content_type, anthropic_api_key, claude_model
                    )
                    
                    if character_analysis.get("has_characters", False):
                        st.session_state.character_analysis = character_analysis
                        st.success(f"✅ Detectados {len(character_analysis['characters'])} personajes para secuencia")
                    else:
                        st.warning("⚠️ No se detectaron personajes. Se generará imagen única.")
                        st.session_state.character_sequence_mode = False
                
                # Paso 2: Generar imagen(es)
                if st.session_state.character_sequence_mode and st.session_state.character_analysis:
                    # Modo secuencia: generar múltiples imágenes
                    status_text.text("🎬 Generando secuencia de imágenes con personajes...")
                    progress_bar.progress(40)
                    
                    flux_config = {
                        "api_key": bfl_api_key,
                        "model": flux_model,
                        "width": image_width,
                        "height": image_height,
                        "steps": flux_steps,
                        "style": image_style
                    }
                    
                    sequence_results = generate_character_sequence(
                        generated_text, content_type, st.session_state.character_analysis, flux_config
                    )
                    
                    if sequence_results["success"]:
                        st.session_state.character_images = sequence_results["character_cards"]
                        st.session_state.sequence_generation_complete = True
                        progress_bar.progress(70)
                    else:
                        st.error("❌ Error generando secuencia de personajes")
                        progress_bar.progress(40)
                else:
                    # Modo normal: generar imagen única
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
                if st.session_state.character_sequence_mode and st.session_state.sequence_generation_complete:
                    st.success("🎉 **¡Generación con secuencia completada!** Tu contenido multimedia con personajes consistentes está listo.")
                else:
                    st.success("🎉 **¡Generación completada!** Tu contenido multimedia está listo.")
                
            else:
                st.error("⚠ Error al generar el contenido de texto con Claude.")
                
        except Exception as e:
            st.error(f"⚠ Error durante la generación: {str(e)}")
            progress_bar.progress(0)
            status_text.text("⚠ Generación fallida")

# NUEVO: Proceso para generar solo secuencia (si ya existe texto)
if generate_sequence_button and st.session_state.generated_content.get('text'):
    if not bfl_api_key:
        st.error("⚠ Necesitas la API key de Black Forest Labs para generar imágenes.")
    else:
        st.info("🎬 Generando solo secuencia de imágenes...")
        
        # Analizar personajes del texto existente
        character_analysis = analyze_characters_with_claude(
            st.session_state.generated_content['text'], 
            st.session_state.generated_content['text_metadata']['content_type'],
            anthropic_api_key, claude_model
        )
        
        if character_analysis.get("has_characters", False):
            st.session_state.character_analysis = character_analysis
            
            flux_config = {
                "api_key": bfl_api_key,
                "model": flux_model,
                "width": image_width,
                "height": image_height,
                "steps": flux_steps,
                "style": image_style
            }
            
            sequence_results = generate_character_sequence(
                st.session_state.generated_content['text'],
                st.session_state.generated_content['text_metadata']['content_type'],
                character_analysis, flux_config
            )
            
            if sequence_results["success"]:
                st.session_state.character_images = sequence_results["character_cards"]
                st.session_state.sequence_generation_complete = True
                st.success("🎉 ¡Secuencia de personajes generada!")
            else:
                st.error("❌ Error generando secuencia")
        else:
            st.warning("⚠️ No se detectaron personajes en el texto para crear secuencia.")
# ===== MOSTRAR CONTENIDO GENERADO DESDE SESSION STATE (MEJORADO CON SECUENCIAS) =====
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

    # NUEVO: Mostrar secuencia de personajes si existe
    if st.session_state.sequence_generation_complete and st.session_state.character_images:
        with image_container:
            st.header("🎭 Secuencia de Personajes Generada por Flux")
            
            total_images = sum(len(card["images"]) for card in st.session_state.character_images)
            st.success(f"✅ Secuencia completada: {len(st.session_state.character_images)} personajes, {total_images} imágenes")
            
            # Mostrar imágenes por personaje
            for i, character_card in enumerate(st.session_state.character_images):
                st.subheader(f"👤 {character_card['name']} (Seed: {character_card['seed']})")
                
                if character_card["images"]:
                    # Crear columnas para mostrar imágenes del personaje
                    cols = st.columns(min(len(character_card["images"]), 3))
                    
                    for j, image_data in enumerate(character_card["images"]):
                        with cols[j % 3]:
                            st.image(
                                image_data["image_obj"], 
                                caption=f"{image_data['scene']}",
                                use_container_width=True
                            )
                            
                            # Mostrar información de la imagen
                            with st.expander(f"📋 Info: {image_data['scene']}"):
                                st.code(image_data["prompt"], language="text")
                                st.caption(f"Seed: {image_data['seed']} | Personaje: {image_data['character_name']}")
                            
                            # Botón de descarga individual
                            st.download_button(
                                label="📥 Descargar",
                                data=image_data["image_bytes"],
                                file_name=f"{character_card['name']}_{image_data['scene'].replace(' ', '_')}.png",
                                mime="image/png",
                                key=f"download_char_img_{i}_{j}_{image_data['timestamp']}"
                            )
                else:
                    st.warning(f"No se generaron imágenes para {character_card['name']}")
            
            # Botón para descargar todas las imágenes como ZIP
            if total_images > 0:
                import zipfile
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for character_card in st.session_state.character_images:
                        for image_data in character_card["images"]:
                            filename = f"{character_card['name']}_{image_data['scene'].replace(' ', '_')}.png"
                            zip_file.writestr(filename, image_data["image_bytes"])
                
                st.download_button(
                    label="📦 Descargar Todas las Imágenes (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"secuencia_personajes_{int(time.time())}.zip",
                    mime="application/zip",
                    key=f"download_all_sequence_{int(time.time())}"
                )
    
    # Mostrar imagen única (modo normal)
    elif 'image_obj' in st.session_state.generated_content:
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
    
    # Estadísticas finales (MEJORADAS CON SECUENCIAS)
    with st.expander("📈 Estadísticas de generación"):
        if st.session_state.sequence_generation_complete:
            # Estadísticas para modo secuencia
            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
            
            text_meta = st.session_state.generated_content.get('text_metadata', {})
            total_images = sum(len(card["images"]) for card in st.session_state.character_images)
            total_characters = len(st.session_state.character_images)
            
            with col_stats1:
                st.metric("Palabras generadas", text_meta.get('word_count', 0))
            with col_stats2:
                st.metric("Personajes detectados", total_characters)
            with col_stats3:
                st.metric("Imágenes en secuencia", total_images)
            with col_stats4:
                content_type = text_meta.get('content_type', 'texto')
                st.metric("Tipo contenido", content_type.title())
        else:
            # Estadísticas para modo normal
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
        st.session_state.character_analysis = None
        st.session_state.character_images = []
        st.session_state.sequence_generation_complete = False
        st.rerun()

# ===== INFORMACIÓN ADICIONAL EN EL FOOTER =====
st.markdown("---")

# Tabs informativas (ACTUALIZADAS CON NUEVAS FUNCIONALIDADES)
tab1, tab2, tab3, tab4 = st.tabs(["📚 Instrucciones", "🔑 APIs", "💡 Consejos", "⚡ Modelos"])

with tab1:
    st.markdown("""
    ### Cómo usar la aplicación:
    
    1. **🔧 Configura las APIs**: Ingresa tus claves en la barra lateral
    2. **✏️ Escribe tu prompt**: Describe detalladamente qué quieres generar  
    3. **📋 Selecciona el tipo**: Ahora con **13 tipologías** diferentes disponibles
    4. **🎭 Activa secuencias**: Para contenido con personajes (opcional)
    5. **⚙️ Personaliza**: Ajusta modelos y configuraciones según tus necesidades
    6. **🚀 Genera**: Presiona el botón y espera tu contenido multimedia completo
    
    ### 🆕 **Nuevas funcionalidades:**
    
    **🎭 Modo Secuencia de Personajes:**
    - Detecta automáticamente personajes en relatos y cuentos
    - Genera múltiples imágenes con el mismo personaje
    - Usa seeds consistentes para mantener apariencia
    - Perfect para cuentos infantiles y material educativo
    
    **📋 13 Tipologías Especializadas:**
    - Cada tipo tiene prompts optimizados
    - Formatos específicos y extensiones adaptadas
    - Ejemplos y plantillas incluidas
    """)

with tab2:
    st.markdown("""
    ### APIs necesarias:
    
    **🧠 Anthropic API (Claude Sonnet 4)**
    - Regístrate en: https://console.anthropic.com/
    - Usado para: Generación de texto + Análisis de personajes + Prompts visuales inteligentes
    
    **🎨 Black Forest Labs API (Flux)**
    - Regístrate en: https://api.bfl.ml/
    - Usado para: Generación de imágenes + Secuencias con seeds consistentes
    
    **🗣️ OpenAI API (TTS)**
    - Regístrate en: https://platform.openai.com/
    - Usado para: Conversión de texto a voz de alta calidad
    """)

with tab3:
    st.markdown("""
    ### Consejos para mejores resultados:
    
    **📝 Para secuencias de personajes:**
    - Describe claramente los personajes en tu relato
    - Incluye características físicas específicas
    - Usa nombres para los personajes principales
    - El sistema funciona mejor con 1-3 personajes
    
    **🎨 Para imágenes:**
    - **Automático Inteligente**: Claude adapta el análisis visual a cada tipología
    - **Personalizado**: Escribe tu prompt EN INGLÉS para control total
    - **Seeds consistentes**: Garantizan el mismo personaje en múltiples imágenes
    """)

with tab4:
    st.markdown("""
    ### Información de los modelos:
    
    **🧠 Claude Sonnet 4 (2025)**
    - Análisis de personajes con IA
    - Generación de prompts visuales optimizados
    - 13 tipologías especializadas de contenido
    
    **🎨 Flux Pro 1.1 / Ultra**
    - Generación de imágenes de alta calidad
    - Soporte para seeds consistentes
    - Múltiples estilos visuales
    
    **🗣️ OpenAI TTS-1-HD**
    - 6 voces diferentes con personalidades únicas
    - Calidad de audio profesional
    
    ### 🎭 **Sistema de Consistencia de Personajes:**
    
    **Cómo funciona:**
    1. Claude analiza el texto y detecta personajes
    2. Extrae características físicas específicas
    3. Genera seed único por personaje
    4. Crea múltiples escenas con el mismo seed
    5. Resultado: Mismo personaje en diferentes situaciones
    
    **Casos de uso perfectos:**
    - Cuentos infantiles con protagonistas
    - Material educativo con personajes recurrentes
    - Relatos con secuencias narrativas
    - Historias que requieren continuidad visual
    """)
