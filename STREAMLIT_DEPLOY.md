# 📊 Despliegue del Dashboard Streamlit

## 🚀 Desplegar en Streamlit Community Cloud

### 1. Configuración Inicial

1. Ve a: https://share.streamlit.io/
2. Sign in con tu cuenta de GitHub
3. Clic en "New app"

### 2. Configuración del App

- **Repository**: `JimeFioni/VialParking_AgentAI_E`
- **Branch**: `main`
- **Main file path**: `dashboard/production.py`
- **App URL** (slug): `vialparking-dashboard` (o el que prefieras)

### 3. ⚙️ Configurar Variables de Entorno (Secrets)

En **Advanced settings → Secrets**, pega el siguiente contenido (ajustando los valores):

```toml
# Configuración de Google Sheets y Drive
ECOGAS_SHEET_ID = "1d2WIsyCIETfMdRgSoE3nk9-bxIO_sySKqTVJHVwMV8Q"
OUTPUT_SHEET_ID = "1qKQxWRcN1bjbavw2BgYPjh0rA0VaoaDfTHt_8COAVKw"
IMAGENES_CARTELES_FOLDER_ID = "19YQCBODmkk_dCssMBB2GuNPfQs5oaUmV"
OUTPUT_IMAGENES_FOLDER_ID = "19YQCBODmkk_dCssMBB2GuNPfQs5oaUmV"

# Contenido del archivo credentials.json (formato JSON inline)
GOOGLE_SHEETS_CREDENTIALS_JSON = '''
{
  "type": "service_account",
  "project_id": "tu-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...",
  "client_id": "...",
  ...
}
'''

# Usuarios autorizados para editar (generar hash con: python -c "import hashlib; print(hashlib.sha256('tu_contraseña'.encode()).hexdigest())")
[users.admin]
password = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"  # Hash de tu contraseña
role = "admin"

[users.jime]
password = "GENERAR_TU_HASH_AQUI"  # Usa el comando de arriba
role = "admin"

[users.operador1]
password = "GENERAR_TU_HASH_AQUI"
role = "viewer"
```

### 4. 🔐 Generar Hash de Contraseñas

Para crear el hash de una contraseña, ejecuta en tu terminal:

```bash
python -c "import hashlib; print(hashlib.sha256('tu_contraseña_aqui'.encode()).hexdigest())"
```

**Ejemplo:**
- Contraseña: `MiClave123!`
- Comando: `python -c "import hashlib; print(hashlib.sha256('MiClave123!'.encode()).hexdigest())"`
- Hash resultante: `240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9`

### 5. ✅ Deploy

Clic en **"Deploy!"** y espera a que se complete el despliegue (2-3 minutos).

---

## 🔒 Sistema de Autenticación

### Roles de Usuario

- **`admin`**: Puede ver y editar todo (WhatsApp, Stock, Empleados)
- **`viewer`**: Solo visualización (igual que modo público)

### Modo Público

El dashboard es **visible para todos** sin login. Las siguientes acciones requieren autenticación:

- ✅ **Público (sin login)**: Ver dashboard, mapa, reportes, estadísticas
- 🔒 **Requiere login**:
  - Registrar trabajos desde PC (pestaña WhatsApp)
  - Registrar movimientos de stock
  - Agregar/editar empleados

### Login en el Dashboard

1. En la barra lateral, expandir **"🔐 Login (Opcional - Solo para editar)"**
2. Ingresar usuario y contraseña
3. Clic en **"Iniciar sesión"**
4. Una vez autenticado, las funciones protegidas se desbloquean

---

## 🌐 Dominio Personalizado (Opcional)

Si quieres usar tu propio dominio `dashboard.vialparking.com.ar`:

1. En Streamlit App → **Settings → Custom domain**
2. Agrega: `dashboard.vialparking.com.ar`
3. En tu DNS, crea un registro CNAME:
   - **Name**: `dashboard`
   - **Target**: `<tu-app>.streamlit.app`
   - **TTL**: 3600

---

## 📝 Notas Importantes

- El plan gratuito de Streamlit Community Cloud:
  - ✅ Perfecto para dashboards
  - ✅ Apps privadas con autenticación
  - ⚠️ El app se "duerme" tras inactividad (se reactiva automáticamente al acceder)
  - ⚠️ Límite de recursos (pero suficiente para este proyecto)

- Si necesitas más recursos o app 24/7:
  - Upgrade a plan pagado ($20/mes)
  - O desplegar en Render como segundo Web Service

---

## 🔧 Actualizar el Dashboard

Streamlit detecta automáticamente cambios en GitHub:

1. Haz cambios en `dashboard/production.py` localmente
2. Push a GitHub: `git push origin main`
3. Streamlit redespliega automáticamente (1-2 min)

O puedes redeployar manualmente desde el panel de Streamlit Cloud.
