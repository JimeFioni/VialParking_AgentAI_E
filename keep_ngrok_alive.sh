#!/bin/bash

echo "🔄 Monitoreando ngrok..."

while true; do
    # Verificar si ngrok está corriendo
    if ! pgrep -x "ngrok" > /dev/null; then
        echo "⚠️  Ngrok no está corriendo. Reiniciando..."
        
        # Iniciar ngrok en background
        nohup ngrok http 8000 > /dev/null 2>&1 &
        sleep 5
        
        # Obtener nueva URL
        URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') and len(d['tunnels'])>0 else '')" 2>/dev/null)
        
        if [ -n "$URL" ]; then
            echo "✅ Ngrok reiniciado!"
            echo "📍 Nueva URL: $URL"
            echo "$URL" > ngrok_url.txt
            echo "$URL/webhook/whatsapp" > webhook_url.txt
            
            # Mostrar advertencia de cambio de URL
            echo ""
            echo "⚠️  LA URL HA CAMBIADO - Actualiza Twilio con:"
            echo "$URL/webhook/whatsapp"
            echo ""
        fi
    else
        # Verificar que la API de ngrok responde
        if ! curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
            echo "⚠️  Ngrok API no responde. Reiniciando..."
            pkill -9 ngrok
            sleep 2
        fi
    fi
    
    # Esperar 10 segundos antes de verificar de nuevo
    sleep 10
done
