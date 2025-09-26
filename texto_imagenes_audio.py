import streamlit as st
import requests
import base64
import io
import time
from PIL import Image
import json
import os
from typing import Optional, Dict, Any

# Configuración de la página
st.set_page_config(
    page_title="Generador de Contenido Multimedia - Claude & Flux",
    page_icon="🎨",
    layout="wide"
)

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
        ["claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219"],
        index=0,
        help="Claude Sonnet 4 es el más reciente y avanzado"
    )
    
    # Configuración de Flux
    flux_model = st.selectbox(
        "Modelo de Flux",
        ["flux-pro-1.1", "flux-pro", "flux-dev"],
        index=0,
        help="Flux Pro 1.1 es la versión más avanzada"
    )
    
    flux_steps = st.slider("Pasos de generación (Flux)", 1, 50, 25, help="Más pasos = mejor calidad pero más tiempo")
    
    # Configuración de audio
    voice_model = st.selectbox(
        "Voz para Audio",
        ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        index=0
    )
    
    # Configuraciones adicionales
    st.subheader("Configuraciones Avanzadas")
    max_tokens_claude = st.number_input("Max tokens Claude", 500, 4000, 2000)
    image_width = st.selectbox("Ancho de imagen", [512, 768, 1024, 1344], index=2)
    image_height = st.selectbox("Alto de imagen", [512, 768, 1024, 1344], index=2)

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

# Función para generar prompt de imagen optimizado para Flux
def create_image_prompt(text_content: str) -> str:
    """Crea un prompt optimizado para Flux basado en el contenido del texto"""
    # Extraer elementos clave del texto para crear un prompt visual efectivo
    content_preview = text_content[:800]  # Usar más contexto para mejor comprensión
    
    # Prompt base optimizado para Flux
    base_prompt = f"Create a high-quality, detailed visual representation of the following content: {content_preview}."
    
    # Agregar especificaciones técnicas para Flux
    technical_specs = " Professional photography style, sharp focus, vibrant colors, excellent composition, 8K resolution, masterpiece quality."
    
    return base_prompt + technical_specs

# Función para generar imagen con Flux
def generate_image_flux(text_content: str, api_key: str, model: str, width: int, height: int, steps: int) -> Optional[Image.Image]:
    """Genera imagen usando Flux de Black Forest Labs"""
    try:
        # Crear prompt optimizado
        image_prompt = create_image_prompt(text_content)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Configuración específica para diferentes modelos de Flux
        data = {
            "prompt": image_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "prompt_upsampling": False,
            "seed": None,  # Aleatorio
            "output_format": "png",
            "safety_tolerance": 2
        }
        
        # URL específica según el modelo
        if model == "flux-pro-1.1":
            url = "https://api.bfl.ml/v1/flux-pro-1.1"
        elif model == "flux-pro":
            url = "https://api.bfl.ml/v1/flux-pro"
        else:  # flux-dev
            url = "https://api.bfl.ml/v1/flux-dev"
        
        # Hacer la petición
        response = requests.post(url, headers=headers, json=data, timeout=180)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Flux devuelve un ID de tarea, necesitamos hacer polling
            task_id = response_data.get("id")
            if task_id:
                return poll_flux_result(task_id, api_key)
            else:
                st.error("No se recibió ID de tarea de Flux")
                return None
        else:
            st.error(f"Error iniciando generación con Flux: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error en la generación de imagen con Flux: {str(e)}")
        return None

# Función para hacer polling del resultado de Flux
def poll_flux_result(task_id: str, api_key: str) -> Optional[Image.Image]:
    """Hace polling para obtener el resultado de la generación de Flux"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # Polling hasta obtener el resultado
        max_attempts = 60  # 5 minutos máximo
        for attempt in range(max_attempts):
            response = requests.get(
                f"https://api.bfl.ml/v1/get_result?id={task_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("status") == "Ready":
                    # Obtener la imagen
                    image_url = result.get("result", {}).get("sample")
                    if image_url:
                        img_response = requests.get(image_url, timeout=60)
                        if img_response.status_code == 200:
                            return Image.open(io.BytesIO(img_response.content))
                    
                elif result.get("status") in ["Error", "Request Moderated"]:
                    st.error(f"Error en Flux: {result.get('status')}")
                    return None
                
                # Si aún está procesando, esperar
                time.sleep(5)
                
            else:
                st.error(f"Error consultando resultado de Flux: {response.status_code}")
                return None
        
        st.error("Timeout esperando resultado de Flux")
        return None
        
    except Exception as e:
        st.error(f"Error en polling de Flux: {str(e)}")
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
        # Progress bar mejorada
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Contenedores para resultados
        text_container = st.container()
        image_container = st.container()
        audio_container = st.container()
        
        try:
            # Paso 1: Generar texto con Claude Sonnet 4
            status_text.text("🧠 Generando contenido con Claude Sonnet 4...")
            progress_bar.progress(20)
            
            generated_text = generate_text_claude(
                user_prompt, content_type, anthropic_api_key, 
                claude_model, max_tokens_claude
            )
            
            if generated_text:
                with text_container:
                    st.header("📄 Contenido Generado por Claude")
                    st.markdown(generated_text)
                    
                    # Métricas del texto
                    word_count = len(generated_text.split())
                    char_count = len(generated_text)
                    st.caption(f"📊 {word_count} palabras • {char_count} caracteres")
                    
                    # Botón para descargar texto
                    st.download_button(
                        label="📥 Descargar Texto",
                        data=generated_text,
                        file_name=f"{content_type}_claude_{int(time.time())}.txt",
                        mime="text/plain"
                    )
                
                progress_bar.progress(40)
                
                # Paso 2: Generar imagen con Flux
                status_text.text("🎨 Generando imagen con Flux (esto puede tomar unos minutos)...")
                progress_bar.progress(50)
                
                generated_image = generate_image_flux(
                    generated_text, bfl_api_key, flux_model,
                    image_width, image_height, flux_steps
                )
                
                if generated_image:
                    with image_container:
                        st.header("🖼️ Imagen Generada por Flux")
                        st.image(generated_image, caption=f"Generada con {flux_model} • {image_width}x{image_height}px")
                        
                        # Convertir imagen a bytes para descarga
                        img_buffer = io.BytesIO()
                        generated_image.save(img_buffer, format="PNG", quality=95)
                        img_bytes = img_buffer.getvalue()
                        
                        st.download_button(
                            label="📥 Descargar Imagen",
                            data=img_bytes,
                            file_name=f"flux_image_{int(time.time())}.png",
                            mime="image/png"
                        )
                
                progress_bar.progress(70)
                
                # Paso 3: Generar audio
                status_text.text("🗣️ Generando narración en audio...")
                progress_bar.progress(80)
                
                generated_audio = generate_audio(generated_text, voice_model, openai_api_key)
                
                if generated_audio:
                    with audio_container:
                        st.header("🎵 Audio Generado")
                        st.audio(generated_audio, format="audio/mp3")
                        
                        # Información del audio
                        audio_size = len(generated_audio) / 1024  # KB
                        st.caption(f"🎧 Voz: {voice_model} • Tamaño: {audio_size:.1f} KB")
                        
                        st.download_button(
                            label="📥 Descargar Audio",
                            data=generated_audio,
                            file_name=f"audio_tts_{int(time.time())}.mp3",
                            mime="audio/mp3"
                        )
                
                # Completado
                progress_bar.progress(100)
                status_text.text("✅ ¡Contenido multimedia generado exitosamente!")
                
                # Resumen final (SIN ANIMACIÓN DE GLOBOS)
                st.success("🎉 **¡Generación completada!** Tu contenido multimedia está listo.")
                
                # Estadísticas finales
                with st.expander("📈 Estadísticas de generación"):
                    col_stats1, col_stats2, col_stats3 = st.columns(3)
                    with col_stats1:
                        st.metric("Palabras generadas", word_count)
                    with col_stats2:
                        st.metric("Resolución imagen", f"{image_width}x{image_height}")
                    with col_stats3:
                        st.metric("Pasos Flux", flux_steps)
                
            else:
                st.error("❌ Error al generar el contenido de texto con Claude.")
                
        except Exception as e:
            st.error(f"❌ Error durante la generación: {str(e)}")
            progress_bar.progress(0)
            status_text.text("❌ Generación fallida")

# Información adicional en el footer
st.markdown("---")

# Tabs informativas
tab1, tab2, tab3, tab4 = st.tabs(["📚 Instrucciones", "🔑 APIs", "💡 Consejos", "⚡ Modelos"])

with tab1:
    st.markdown("""
    ### Cómo usar la aplicación:
    
    1. **🔧 Configura las APIs**: Ingresa tus claves en la barra lateral
    2. **✏️ Escribe tu prompt**: Describe detalladamente qué quieres generar  
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
    - El prompt de imagen se genera automáticamente del texto
    - Flux Pro 1.1 ofrece la mejor calidad
    - Imágenes más grandes requieren más tiempo de procesamiento
    
    **🎵 Para el audio:**
    - El texto se limpia automáticamente para TTS
    - Textos muy largos se truncan a 4000 caracteres
    - Diferentes voces tienen personalidades distintas
    """)

with tab4:
    st.markdown("""
    ### Información de los modelos:
    
    **🧠 Claude Sonnet 4**
    - Modelo de lenguaje más avanzado de Anthropic
    - Excelente para razonamiento y escritura creativa
    - Contexto largo y respuestas de alta calidad
    
    **🎨 Flux (Black Forest Labs)**
    - **Flux Pro 1.1**: La versión más avanzada, mejor calidad
    - **Flux Pro**: Versión estable y rápida
    - **Flux Dev**: Para experimentación y desarrollo
    
    **🗣️ OpenAI TTS-1-HD**
    - Modelo de alta definición para síntesis de voz
    - 6 voces diferentes con personalidades únicas
    - Calidad de audio profesional
    """)
