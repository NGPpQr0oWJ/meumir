import ntplib
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

# Список NTP серверов
NTP_SERVERS = [
    'pool.ntp.org',
    'time.windows.com',
    'time.google.com'
]

# Московское смещение в часах
MOSCOW_OFFSET = 3

def get_server_time():
    """
    Получает текущее время с NTP сервера с учетом московского часового пояса.
    В случае ошибки возвращает локальное время системы.
    """
    ntp_client = ntplib.NTPClient()
    
    for server in NTP_SERVERS:
        try:
            response = ntp_client.request(server, timeout=2)
            utc_time = datetime.fromtimestamp(response.tx_time, timezone.utc)
            moscow_time = utc_time + timedelta(hours=MOSCOW_OFFSET)
            logger.info(f"Время успешно получено с сервера {server}")
            return moscow_time
        except Exception as e:
            logger.warning(f"Ошибка получения времени с сервера {server}: {e}")
            continue
    
    # Если не удалось получить время с серверов, используем системное время
    local_time = datetime.now()
    logger.warning("Используется системное время, так как не удалось получить время с серверов")
    return local_time
