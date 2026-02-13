# 🔐 Guía de Tokens OAuth para Google Drive

## ⏱️ Duración de Tokens

### Access Token
- **Duración**: 1 hora (NO se puede cambiar)
- **Se renueva automáticamente** con el Refresh Token
- El sistema lo maneja sin intervención

### Refresh Token
Duración depende del estado de la app en Google Cloud:

| Estado de la App | Duración del Refresh Token |
|-----------------|---------------------------|
| 🧪 **Testing** (modo desarrollo) | **7 días** ⚠️ |
| ✅ **Production** (publicada) | **6 meses** o indefinido |

## ⚠️ PROBLEMA ACTUAL

Tu app está en modo **Testing**, por eso:
- ✅ Access token se renueva cada hora (automático)
- ❌ Refresh token expira cada **7 días**
- ❌ Cada 7 días debes ejecutar `python setup_oauth_drive.py`

## ✅ SOLUCIÓN: Publicar la App OAuth

### Opción 1: Publicar en Producción (Recomendado)
1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Selecciona tu proyecto: **vialp-483820**
3. **APIs & Services** → **OAuth consent screen**
4. Click en **PUBLISH APP**
5. Confirma la publicación

**Ventajas:**
- ✅ Refresh token dura 6+ meses
- ✅ Se renueva automáticamente
- ✅ No requiere intervención manual

**Desventajas:**
- Requiere verificación de Google (si pides scopes sensibles)
- Para `/auth/drive.file` (tu caso) NO requiere verificación

### Opción 2: Mantener en Testing + Añadir Usuarios
Si prefieres mantener en Testing:
1. **OAuth consent screen** → **Test users**
2. Añade tu email y otros usuarios que necesiten acceso
3. Ejecuta `python setup_oauth_drive.py` cada 7 días

## 🔧 Scripts de Mantenimiento

### Renovar Token Manualmente
```bash
python setup_oauth_drive.py
```

### Verificar Estado del Token
```bash
python check_oauth_token.py
```

### Cron Job (Linux/Mac) - Verificar cada día
```bash
# Editar crontab
crontab -e

# Añadir línea (ejecuta a las 3 AM cada día)
0 3 * * * cd /ruta/a/VialP_Ecogas && /usr/bin/python3 check_oauth_token.py >> /tmp/oauth_check.log 2>&1
```

### Task Scheduler (Windows)
Crear tarea programada que ejecute:
```
python check_oauth_token.py
```
Cada día a las 3 AM

## 📊 Monitoreo

El sistema muestra warnings cuando:
- Token expirará en menos de 5 minutos
- Token sin refresh_token
- Error al renovar

## 🚀 Producción (Render/Streamlit Cloud)

En producción, usa la variable `DRIVE_OAUTH_TOKEN_BASE64`:

```bash
# Generar token para producción
python3 -c "import pickle, base64, json; 
token = pickle.load(open('token_drive.pickle', 'rb')); 
data = {
    'token': token.token,
    'refresh_token': token.refresh_token,
    'token_uri': token.token_uri,
    'client_id': token.client_id,
    'client_secret': token.client_secret,
    'scopes': token.scopes
}; 
print(base64.b64encode(json.dumps(data).encode()).decode())"
```

Copia el resultado y configúralo en Render/Streamlit como `DRIVE_OAUTH_TOKEN_BASE64`.

## 📝 Resumen

| Acción | Frecuencia | Comando |
|--------|-----------|---------|
| Renovar token (Testing) | Cada 7 días | `python setup_oauth_drive.py` |
| Verificar token | Diario (automático) | `python check_oauth_token.py` |
| Publicar app | Una vez | Google Cloud Console |
| Actualizar Render | Al renovar | Copiar nuevo token base64 |

## ❓ FAQ

**P: ¿Por qué expira cada 7 días?**
R: Tu app está en modo Testing. Publícala para extender a 6 meses.

**P: ¿Puedo hacer que el access token dure más?**
R: No, Google limita a 1 hora. Usa refresh token para renovación automática.

**P: ¿Qué pasa si se revoca el acceso?**
R: Debes ejecutar `setup_oauth_drive.py` nuevamente.

**P: ¿El sistema se cae si expira el token?**
R: No, pero las imágenes NO se subirán a Drive. El registro en planilla sí funcionará.
