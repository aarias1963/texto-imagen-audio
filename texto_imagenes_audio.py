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
        
        # Prompts específicos y mejorados para Claude
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
Formato: Estructura narrativa clásica con introducción, desarrollo, clímax y desenlace."""
        }
        
        user_message = f"""Crea un {content_type} sobre: {prompt}

Por favor, asegúrate de que el contenido sea:
1. Completo y bien desarrollado
2. Apropiado para el tipo de contenido solicitado
3. Interesante y bien escrito
4. Listo para ser presentado como contenido final

El {content_type} debe tener la extensión apropiada para su tipo y propósito."""
        
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

# Función para optimizar prompt para Flux (basada en el archivo de referencia)
def optimize_prompt_for_flux(prompt, style="photorealistic"):
    """Optimiza el prompt para mejor generación de imágenes con el estilo seleccionado"""
    try:
        # Definir estilos específicos
        style_prompts = {
            "photorealistic": "Photorealistic, high-quality photograph of: {prompt}. Professional photography, realistic lighting, sharp focus, detailed textures, natural colors, 8K resolution, masterpiece quality, cinematic composition",
            "digital-art": "High-quality digital artwork of: {prompt}. Professional digital art, vibrant colors, sharp focus, detailed illustration, artistic composition, masterpiece",
            "cinematic": "Cinematic scene of: {prompt}. Movie-like composition, dramatic lighting, professional cinematography, high production value, detailed scene, 8K quality",
            "documentary": "Documentary-style photograph of: {prompt}. Authentic, candid photography, natural lighting, real-world setting, journalistic quality, unposed, realistic",
            "portrait": "Professional portrait of: {prompt}. Studio lighting, sharp focus, detailed features, high-quality photography, professional composition, realistic skin tones"
        }
        
        # Usar el estilo seleccionado o el por defecto
        template = style_prompts.get(style, style_prompts["photorealistic"])
        optimized = template.format(prompt=prompt)
        
        return optimized
    except Exception as e:
        st.error(f"Error optimizando prompt: {str(e)}")
        return prompt

# Función para generar imagen con Flux Pro (basada en el archivo de referencia)
def generate_image_flux_pro(prompt, width, height, steps, api_key, style="photorealistic"):
    """Genera imagen usando Flux Pro 1.1 (basado en implementación funcional)"""
    optimized_prompt = optimize_prompt_for_flux(prompt, style)
    
    headers = {
        'accept': 'application/json',
        'x-key': api_key,
        'Content-Type': 'application/json',
    }
    
    json_data = {
        'prompt': optimized_prompt,
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
    
    return process_flux_response(response, api_key), optimized_prompt

# Función para generar imagen con Flux Ultra (basada en el archivo de referencia)  
def generate_image_flux_ultra(prompt, aspect_ratio, api_key, style="photorealistic"):
    """Genera imagen usando Flux Pro 1.1 Ultra (basado en implementación funcional)"""
    optimized_prompt = optimize_prompt_for_flux(prompt, style)
    
    headers = {
        'accept': 'application/json',
        'x-key': api_key,
        'Content-Type': 'application/json',
    }
    
    json_data = {
        'prompt': optimized_prompt,
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
    
    return process_flux_response(response, api_key), optimized_prompt

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

# Función principal para generar imagen con Flux
def generate_image_flux(text_content: str, api_key: str, model: str, width: int, height: int, steps: int, style: str = "photorealistic", custom_prompt: str = None) -> Optional[Image.Image]:
    """Genera imagen usando Flux (wrapper que usa la implementación funcional)"""
    try:
        # Determinar qué prompt usar
        if custom_prompt and custom_prompt.strip():
            # Usar el prompt personalizado del usuario
            visual_prompt = custom_prompt.strip()
            st.info(f"🎨 Usando prompt personalizado para la imagen")
        else:
            # Generar prompt automáticamente desde el texto
            content_preview = ' '.join(text_content.split()[:80])  # Primeras 80 palabras
            visual_prompt = f"A realistic scene representing: {content_preview}. Real world setting, natural environment, authentic details"
            st.info(f"🤖 Generando prompt automático desde el contenido")
        
        if model == "flux-pro-1.1-ultra":
            # Usar Ultra con aspect ratio
            aspect_ratio = f"{width}:{height}" if width == height else "16:9"
            result, optimized_prompt = generate_image_flux_ultra(visual_prompt, aspect_ratio, api_key, style)
        else:
            # Usar Pro normal
            result, optimized_prompt = generate_image_flux_pro(visual_prompt, width, height, steps, api_key, style)
        
        # Mostrar el prompt final optimizado
        st.info(f"📝 Prompt final optimizado para Flux: {optimized_prompt}")
        
        if isinstance(result, Image.Image):
            return result
        else:
            st.error(f"Error en Flux: {result}")
            return None
            
    except Exception as e:
        st.error(f"Error en la generación de imagen con Flux: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None

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

# Interfaz principal
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Generación de Contenido")
    
    # Input del usuario con ejemplos
    user_prompt = st.text_area(
        "Describe tu idea:",
        placeholder="""Ejemplos:
• Un tutorial sobre machine learning para principiantes
• Un artículo sobre el futuro de la energía renovable  
• Un cuento sobre un gato que viaja en el tiempo
• Ejercicios de matemáticas para secundaria sobre funciones""",
        height=120
    )
    
    # Tipo de contenido
    content_type = st.selectbox(
        "Tipo de contenido a generar:",
        ["ejercicio", "artículo", "texto", "relato"],
        help="Selecciona el tipo que mejor se adapte a tu necesidad"
    )
    
    # Prompt opcional para imagen
    st.subheader("🖼️ Personalización de Imagen (Opcional)")
    image_prompt = st.text_area(
        "Prompt personalizado para la imagen:",
        placeholder="""Opcional: Describe específicamente qué imagen quieres generar.
Si lo dejas vacío, se generará automáticamente basado en el contenido del texto.

Ejemplos:
• Una persona estudiando con libros de matemáticas en una biblioteca moderna
• Un paisaje futurista con paneles solares y turbinas eólicas
• Un gato naranja con sombrero viajando en una máquina del tiempo steampunk""",
        height=80,
        help="Si especificas un prompt, este se usará en lugar del generado automáticamente"
    )

with col2:
    st.header("🚀 Generación")
    
    # Información del modelo
    st.info(f"🧠 **Claude**: {claude_model}\n\n🎨 **Flux**: {flux_model}\n\n🗣️ **Voz**: {voice_model}")
    
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

# Proceso de generación
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
            status_text.text("🧠 Generando contenido con Claude Sonnet 4...")
            progress_bar.progress(20)
            
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
                
                progress_bar.progress(40)
                
                # Paso 2: Generar imagen con Flux
                status_text.text("🎨 Generando imagen con Flux (esto puede tomar unos minutos)...")
                progress_bar.progress(50)
                
                generated_image = generate_image_flux(
                    generated_text, bfl_api_key, flux_model,
                    image_width, image_height, flux_steps, image_style, image_prompt
                )
                
                if generated_image:
                    # Guardar imagen en session state
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
                        'timestamp': int(time.time())
                    }
                
                progress_bar.progress(70)
                
                # Paso 3: Generar audio
                status_text.text("🗣️ Generando narración en audio...")
                progress_bar.progress(80)
                
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

# Mostrar contenido generado desde session state
if st.session_state.generation_complete and st.session_state.generated_content:
    # Contenedores para resultados
    text_container = st.container()
    image_container = st.container()
    audio_container = st.container()
    
    # Mostrar texto
    if 'text' in st.session_state.generated_content:
        with text_container:
            st.header("📄 Contenido Generado por Claude")
            st.markdown(st.session_state.generated_content['text'])
            
            # Métricas del texto
            metadata = st.session_state.generated_content.get('text_metadata', {})
            word_count = metadata.get('word_count', 0)
            char_count = metadata.get('char_count', 0)
            content_type = metadata.get('content_type', 'texto')
            
            st.caption(f"📊 {word_count} palabras • {char_count} caracteres")
            
            # Botón para descargar texto con key única
            text_timestamp = metadata.get('timestamp', int(time.time()))
            st.download_button(
                label="📥 Descargar Texto",
                data=st.session_state.generated_content['text'],
                file_name=f"{content_type}_claude_{text_timestamp}.txt",
                mime="text/plain",
                key=f"download_text_{text_timestamp}"
            )
    
    # Mostrar imagen
    if 'image_obj' in st.session_state.generated_content:
        with image_container:
            st.header("🖼️ Imagen Generada por Flux")
            
            metadata = st.session_state.generated_content.get('image_metadata', {})
            width = metadata.get('width', 'N/A')
            height = metadata.get('height', 'N/A')
            model = metadata.get('model', 'N/A')
            style = metadata.get('style', 'N/A')
            custom_prompt_used = metadata.get('custom_prompt', False)
            
            # Descripción mejorada
            prompt_info = "Con prompt personalizado" if custom_prompt_used else "Generado automáticamente"
            caption = f"Generada con {model} • {width}x{height}px • Estilo: {style} • {prompt_info}"
            
            st.image(
                st.session_state.generated_content['image_obj'], 
                caption=caption
            )
            
            # Información adicional
            if custom_prompt_used:
                st.success("✨ Se utilizó tu prompt personalizado para la imagen")
            else:
                st.info("🤖 Se generó automáticamente basándose en el contenido del texto")
            
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
    
    # Estadísticas finales
    with st.expander("📈 Estadísticas de generación"):
        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        
        text_meta = st.session_state.generated_content.get('text_metadata', {})
        image_meta = st.session_state.generated_content.get('image_metadata', {})
        audio_meta = st.session_state.generated_content.get('audio_metadata', {})
        
        with col_stats1:
            st.metric("Palabras generadas", text_meta.get('word_count', 0))
        with col_stats2:
            width = image_meta.get('width', 0)
            height = image_meta.get('height', 0)
            st.metric("Resolución imagen", f"{width}x{height}" if width and height else "N/A")
        with col_stats3:
            st.metric("Pasos Flux", image_meta.get('steps', 0))
        with col_stats4:
            prompt_type = "Personalizado" if image_meta.get('custom_prompt', False) else "Automático"
            st.metric("Tipo de prompt", prompt_type)
    
    # Botón para limpiar y empezar de nuevo
    if st.button("🔄 Generar Nuevo Contenido", type="secondary"):
        st.session_state.generated_content = {}
        st.session_state.generation_complete = False
        st.rerun()

# Información adicional en el footer
st.markdown("---")

# Tabs informativas
tab1, tab2, tab3, tab4 = st.tabs(["📚 Instrucciones", "🔑 APIs", "💡 Consejos", "⚡ Modelos"])

with tab1:
    st.markdown("""
    ### Cómo usar la aplicación:
    
    1. **🔧 Configura las APIs**: Ingresa tus claves en la barra lateral
    2. **✍️ Escribe tu prompt**: Describe detalladamente qué quieres generar  
    3. **📋 Selecciona el tipo**: Elige entre ejercicio, artículo, texto o relato
    4. **⚙️ Personaliza**: Ajusta modelos y configuraciones según tus necesidades
    5. **🚀 Genera**: Presiona el botón y espera tu contenido multimedia completo
    """)

with tab2:
    st.markdown("""
    ### APIs necesarias:
    
    **🧠 Anthropic API (Claude)**
    - Regístrate en: https://console.anthropic.com/
    - Crea una API key en tu dashboard
    - Usado para generación de texto de alta calidad
    
    **🎨 Black Forest Labs API (Flux)**
    - Regístrate en: https://api.bfl.ml/
    - Obtén tu API key del panel de control  
    - Usado para generación de imágenes de última generación
    
    **🗣️ OpenAI API (TTS)**
    - Regístrate en: https://platform.openai.com/
    - Crea una API key en tu cuenta
    - Usado para conversión de texto a voz
    """)

with tab3:
    st.markdown("""
    ### Consejos para mejores resultados:
    
    **📝 Para el texto:**
    - Sé específico y detallado en tu prompt
    - Incluye el contexto y audiencia objetivo
    - Especifica el tono deseado (formal, casual, técnico, etc.)
    
    **🖼️ Para las imágenes:**
    - **Automático**: Se genera basándose en el contenido del texto
    - **Personalizado**: Describe exactamente qué quieres ver en la imagen
    - **Estilos disponibles**: Photorealistic, Digital-art, Cinematic, Documentary, Portrait
    - **Ejemplos de prompts buenos**: "Una profesora explicando matemáticas en un aula moderna con tecnología", "Paneles solares en un campo al atardecer con montañas de fondo"
    
    **🎵 Para el audio:**
    - El texto se limpia automáticamente para TTS
    - Textos muy largos se truncan a 4000 caracteres
    - Diferentes voces tienen personalidades distintas
    """)

with tab4:
    st.markdown("""
    ### Información de los modelos:
    
    **🧠 Claude Sonnet 4 (2025)**
    - Modelo más avanzado de Anthropic
    - claude-sonnet-4-20250514: La versión más reciente
    - Excelente razonamiento, creatividad y contexto largo
    
    **🎨 Flux (Black Forest Labs)**
    - **Flux Pro 1.1**: Control total de dimensiones, excelente calidad
    - **Flux Pro 1.1 Ultra**: Máxima calidad, aspect ratios automáticos
    - Generación de imágenes de última generación
    
    **🗣️ OpenAI TTS-1-HD**
    - Modelo de alta definición para síntesis de voz
    - 6 voces diferentes con personalidades únicas
    - Calidad de audio profesional
    """)
