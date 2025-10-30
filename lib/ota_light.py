# lib/ota_light.py
import os, ujson, usocket, ussl, uhashlib, machine, time
from phew import logging

MANIFEST_URL = "https://raw.githubusercontent.com/eduardokum/enviro/main/releases/manifest.json"
WORK_DIR = "/ota"
BUFFER_SIZE = 1024
LAST_CHECK_FILE = "/ota/last_check.txt"
CHECK_INTERVAL_HOURS = 24  # verifica OTA a cada 24 horas

def _https_get(url):
    _, _, host, *path = url.split("/", 3)
    path = "/" + (path[0] if path else "")
    ai = usocket.getaddrinfo(host, 443)[0][-1]
    s = usocket.socket()
    s.connect(ai)
    s = ussl.wrap_socket(s, server_hostname=host)
    s.write("GET {} HTTP/1.0\r\nHost: {}\r\nUser-Agent: pico-ota\r\nConnection: close\r\n\r\n".format(path, host))
    while s.readline() != b"\r\n":
        pass
    data = b""
    while True:
        chunk = s.read(BUFFER_SIZE)
        if not chunk:
            break
        data += chunk
    s.close()
    return data

def _sha256(b):
    h = uhashlib.sha256()
    h.update(b)
    return "".join("{:02x}".format(x) for x in h.digest())

def _safe_write(path, data):
    dirs = path.split("/")[:-1]
    p = ""
    for d in dirs:
        if not d: continue
        p += "/" + d
        try: os.mkdir(p)
        except OSError: pass
    tmp = path + ".part"
    with open(tmp, "wb") as f: f.write(data)
    try: os.remove(path)
    except OSError: pass
    os.rename(tmp, path)

def _read_file(path):
    try:
        with open(path, "rb") as f: return f.read()
    except: return None

def check_and_update(current_version="0.0.0"):
    logging.info("[OTA] Verificando versão...")
    mraw = _https_get(MANIFEST_URL)
    manifest = ujson.loads(mraw)
    if manifest.get("version") == current_version:
        logging.info("[OTA] Firmware já atualizado.")
        return False

    logging.info("[OTA] Nova versão:", manifest["version"])
    for f in manifest["files"]:
        path = f["path"]
        url = f["url"]
        expected = f["sha256"]
        local = _read_file(path)
        if local and _sha256(local) == expected:
            continue
        logging.info("[OTA] Atualizando:", path)
        data = _https_get(url)
        if _sha256(data) != expected:
            logging.info("[OTA] Hash incorreto, pulando", path)
            continue
        _safe_write(path, data)

    logging.info("[OTA] Atualização concluída. Reiniciando...")
    time.sleep(2)
    machine.reset()
    return True


def _read_last_check():
    try:
        with open(LAST_CHECK_FILE, "r") as f:
            return float(f.read().strip())
    except:
        return 0.0

def _write_last_check(ts):
    os.makedirs("/ota", exist_ok=True)
    with open(LAST_CHECK_FILE, "w") as f:
        f.write(str(ts))

def _rtc_timestamp():
    # Retorna timestamp baseado no RTC do Pico (segundos desde epoch)
    try:
        y, m, d, wd, hh, mm, ss, _ = machine.RTC().datetime()
        import utime
        return utime.mktime((y, m, d, hh, mm, ss, 0, 0))
    except:
        return time.time()

def should_check_ota():
    """Retorna True se passou o intervalo definido desde a última verificação OTA."""
    last_ts = _read_last_check()
    now = _rtc_timestamp()
    hours = (now - last_ts) / 3600.0 if last_ts else CHECK_INTERVAL_HOURS + 1
    if hours >= CHECK_INTERVAL_HOURS:
        _write_last_check(now)
        return True
    return False