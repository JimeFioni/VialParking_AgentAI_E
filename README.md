# VialP ECOGAS - Sistema de Gestión de Cartelería para Gasoductos

Sistema inteligente de gestión de cartelería vial para la red de gasoductos de ECOGAS en Argentina, con agente AI Gemini y geolocalización automática.

## 🎯 Características Principales

- 🤖 **Agente AI con Gemini** para procesamiento de imágenes de carteles
- 📱 **WhatsApp Integration** para operarios en campo
- 🗺️ **Geolocalización automática** de 287 carteles en la red ECOGAS
- 📊 **Dashboard interactivo** con Streamlit para presentaciones
- 📦 **Gestión de stock** automática con alertas
- ☁️ **Google Drive** almacenamiento organizado de imágenes por item
- 📋 **Google Sheets** integración con planilla ECOGAS
- ✅ **Validación de acciones** autorizadas por zona

## 📦 Tecnologías

- **Backend**: FastAPI + Python 3.13
- **AI/ML**: Google Gemini Pro Vision
- **WhatsApp**: Twilio API + ngrok
- **Storage**: Google Drive API
- **Database**: Google Sheets API + SQLAlchemy
- **Frontend**: Streamlit Dashboard
- **Maps**: Folium + Geopy
- **Tunnel**: ngrok para webhooks

## 🚀 Instalación

```bash
# Clonar repositorio
cd VialP_Ecogas

# Crear entorno virtual
python -m venv vialp
source vialp/bin/activate  # En Windows: vialp\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## ⚙️ Configuración

### 1. Google Cloud APIs

1. Crear proyecto en Google Cloud Console
2. Habilitar APIs: Sheets API, Drive API
3. Crear Service Account y descargar `credentials.json`
4. Compartir planilla ECOGAS con el email del Service Account
5. Obtener Gemini API Key desde [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Twilio WhatsApp

1. Crear cuenta en [Twilio](https://www.twilio.com)
2. Configurar WhatsApp Sandbox
3. Obtener Account SID y Auth Token
4. Configurar webhook con ngrok

### 3. Variables de Entorno

Configurar en `.env`:

```env
# Gemini AI
GEMINI_API_KEY=tu_api_key

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
ECOGAS_SHEET_ID=1d2WIsyCIETfMdRgSoE3nk9-bxIO_sySKqTVJHVwMV8Q
IMAGENES_CARTELES_FOLDER_ID=1QszrmYD6QwFpu_M8Wsg9T1PPr6tJPzls

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
ADMIN_WHATSAPP_NUMBER=whatsapp:+549XXXXXXXXXX

# Database
DATABASE_URL=sqlite:///./vialp.db
```

## 🎮 Uso

### Iniciar Backend API

```bash
# Activar entorno virtual
source vialp/bin/activate

# Iniciar servidor FastAPI
uvicorn app.main:app --reload --port 8000
```

### Iniciar Túnel ngrok

```bash
# En otra terminal
ngrok http 8000

# Copiar URL HTTPS y configurar en Twilio webhook:
# https://XXXXX.ngrok-free.app/webhook/whatsapp
```

### Iniciar Dashboard de Demo

```bash
# En otra terminal con el entorno activado
streamlit run dashboard/demo.py
```

El dashboard estará disponible en: `http://localhost:8501`

## 📱 Flujo de Trabajo WhatsApp

1. **Operario envía imagen** del cartel → Sistema descarga y almacena
2. **Operario envía ubicación GPS** → Sistema busca cartel más cercano (radio 5km)
3. **Sistema identifica item** → Busca en planilla ECOGAS por coordenadas
4. **Crea carpeta en Drive** → Organiza por número de item (001, 002, etc.)
5. **Sube imagen a carpeta** → Almacenamiento permanente
6. **Actualiza planilla** → Columna W con enlace a carpeta Drive
7. **Responde al operario** → Tipo de cartel, observaciones y distancia

## 📊 Demo Dashboard

El dashboard interactivo incluye:

- **📈 Métricas en tiempo real**: Total de carteles, trabajos realizados, stock disponible
- **🗺️ Mapa interactivo**: Visualización de los 287 carteles en la red
- **💬 Simulador WhatsApp**: Demostración del flujo de conversación
- **📸 Galería de imágenes**: Imágenes procesadas por el sistema
- **📋 Trabajos realizados**: Historial de intervenciones
- **📦 Stock actual**: Inventario por tipo de cartel

## 🗂️ Estructura del Proyecto

```
VialP/
## 🗂️ Estructura del Proyecto

```
VialP_Ecogas/
├── app/                          # FastAPI Backend
│   ├── main.py                   # Webhook de Twilio y endpoints
│   ├── models.py                 # Modelos SQLAlchemy
│   └── database.py               # Configuración DB
├── agent/                        # Agente AI
│   └── gemini_agent.py           # Gemini Pro Vision
├── services/                     # Servicios externos
│   ├── whatsapp.py              # Twilio WhatsApp API
│   ├── google_sheets.py         # Google Sheets + Drive API
│   └── geolocation.py           # Cálculos de distancia GPS
├── dashboard/                    # Frontend
│   ├── demo.py                  # Dashboard Streamlit demo
│   └── app.py                   # Dashboard principal
├── data/                        # Datos de prueba
├── vialp/                       # Entorno virtual
├── credentials.json             # Google Service Account
├── requirements.txt             # Dependencias Python
├── .env                         # Variables de entorno
├── README.md                    # Este archivo
├── SETUP_GUIDE.md              # Guía detallada
└── GOOGLE_SETUP.md             # Setup Google APIs
```

## 📋 Base de Datos

### Google Sheets - Planilla ECOGAS

- **287 carteles** con georreferencias (Columna 4: lat lon)
- **Columna W (23)**: Enlaces a carpetas Drive con imágenes
- **Datos por cartel**: Gasoducto, Tipo, Observaciones, Coordenadas GPS

### SQLite Local

- **Trabajos**: Registro de intervenciones realizadas
- **Conversaciones**: Historial de mensajes WhatsApp
- **Empleados**: Datos de operarios

## 🔧 Desarrollo

### Testing Local

```bash
# Test webhook localmente
python -c "from services.google_sheets import GoogleSheetsService; gs = GoogleSheetsService(); print(gs.obtener_carteles_ecogas()[:3])"

# Test geolocalización
python -c "from services.geolocation import GeolocationService; geo = GeolocationService(); print(geo.validar_en_argentina(-33.16225, -64.38010))"
```

### Logs

```bash
# Ver logs del servidor
tail -f uvicorn.log

# Verificar proceso
ps aux | grep uvicorn
```

## 🐛 Troubleshooting

### Twilio Webhook no recibe requests

1. Verificar que ngrok esté corriendo: `curl https://XXXXX.ngrok-free.app`
2. Verificar webhook en Twilio Console
3. Revisar logs de ngrok: Ver terminal de ngrok

### Error al descargar imagen de Twilio

- Asegurarse de que `httpx` tenga `follow_redirects=True`
- Twilio URLs requieren autenticación con Account SID y Auth Token

### Google Sheets API error

1. Verificar que `credentials.json` existe
2. Verificar que Service Account tiene permisos en la planilla
3. Sheet ID correcto en `.env`

## 📝 Notas

- **Límite Twilio Sandbox**: 50 mensajes por día
- **Radio de búsqueda**: 5km para encontrar cartel más cercano
- **Validación GPS**: Solo coordenadas dentro de Argentina
- **Formato de coordenadas**: `-33.16225 -64.38010` (lat lon)

## 🤝 Contribuir

1. Fork el proyecto
2. Crear branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial para ECOGAS.

## 👥 Contacto

Sistema desarrollado para la gestión de cartelería de gasoductos ECOGAS.

---

**Última actualización**: Enero 2026
