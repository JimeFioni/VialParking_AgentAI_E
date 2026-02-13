#!/usr/bin/env python3
"""
Cron job para monitoreo automático de token OAuth.
Ejecutar diariamente para verificar estado del token.
"""

import sys
sys.path.append('/Users/Jime/Desktop/Proyects/VialP_Ecogas')

from services.token_monitor import TokenMonitor

if __name__ == "__main__":
    monitor = TokenMonitor()
    result = monitor.check_and_alert(threshold_days=2)
    
    # Exit code para cron
    if result['status'] in ['alert_sent', 'alert_saved']:
        sys.exit(1)  # Indica que se envió alerta
    elif result['status'] == 'error':
        sys.exit(2)  # Indica error
    else:
        sys.exit(0)  # Todo OK
