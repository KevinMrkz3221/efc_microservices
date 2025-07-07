from core.config import settings as SETTINGS
from dataclasses import dataclass
import requests
import httpx
import datetime
import time

class SOAPController:
    """
    Controlador para manejar las peticiones SOAP.
    """

    def __init__(self):
        self.base_url = SETTINGS.SOAP_SERVICE_URL
        self.timeout = SETTINGS.TIMEOUT  # Timeout por default

    def make_request(self, endpoint, data=None, headers=None, max_retries=5):
        intento = 0
        while intento < SETTINGS.MAX_RETRIES:
            try:
                with httpx.Client(verify=SETTINGS.context, timeout=self.timeout) as client:
                    content = data.encode('utf-8') if data else None
                    response = client.post(
                        f"{self.base_url}/{endpoint}",
                        content=content,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response  # ✅ éxito
            except Exception as e:
                intento += 1
                wait_time = 0
                print(f"[{endpoint}] Error intento {intento}: {e}. Reintentando en {SETTINGS.WAIT_TIME}s...")
                time.sleep(SETTINGS.WAIT_TIME)

        print(f"[{endpoint}] Fallo tras {SETTINGS.MAX_RETRIES} intentos.")
        return None
