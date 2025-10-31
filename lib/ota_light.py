import os
import json
import time
import network
import urequests
import logging

OTA_CHECK_INTERVAL = 3600 * 6  # check every 6 hours
OTA_INFO_FILE = "/data/ota_info.json"
OTA_TEMP_FILE = "/data/ota_tmp.py"
OTA_TARGET_FILE = "/main.py"

def ensure_dir(path):
    """Create directories recursively (MicroPython compatible)."""
    parts = path.split("/")
    current = ""
    for p in parts:
        if not p:
            continue
        current += "/" + p
        try:
            os.mkdir(current)
        except OSError:
            pass  # already exists


def _read_last_check():
    try:
        with open(OTA_INFO_FILE, "r") as f:
            data = json.load(f)
        return data.get("last_check", 0)
    except Exception:
        return 0


def _write_last_check(timestamp=None):
    ensure_dir("/data")
    if timestamp is None:
        timestamp = time.time()
    try:
        with open(OTA_INFO_FILE, "w") as f:
            json.dump({"last_check": timestamp}, f)
        logging.debug("[OTA] last check time saved successfully")
    except Exception as e:
        logging.error("[OTA] failed to write last check file: %s", e)


def should_check_ota():
    """Return True if it's time to check for updates."""
    last = _read_last_check()
    now = time.time()
    if (now - last) > OTA_CHECK_INTERVAL:
        logging.info("[OTA] Update check required (last: %s sec ago)", int(now - last))
        return True
    logging.debug("[OTA] Skipping OTA check — last check too recent.")
    return False


def download_update(url):
    """Download new firmware to temp file."""
    try:
        logging.info("[OTA] Downloading update from %s", url)
        r = urequests.get(url)
        if r.status_code != 200:
            logging.error("[OTA] Download failed — HTTP %s", r.status_code)
            return False
        with open(OTA_TEMP_FILE, "w") as f:
            f.write(r.text)
        r.close()
        logging.info("[OTA] Firmware downloaded successfully to temp file")
        return True
    except Exception as e:
        logging.error("[OTA] Exception while downloading: %s", e)
        return False


def apply_update():
    """Replace main.py with downloaded version and reboot."""
    try:
        if not os.path.exists(OTA_TEMP_FILE):
            logging.warning("[OTA] No update file found to apply.")
            return False
        if os.path.exists(OTA_TARGET_FILE):
            os.remove(OTA_TARGET_FILE)
        os.rename(OTA_TEMP_FILE, OTA_TARGET_FILE)
        logging.info("[OTA] Firmware update applied successfully — rebooting...")
        _write_last_check()
        import machine
        machine.reset()
        return True
    except Exception as e:
        logging.error("[OTA] Failed to apply update: %s", e)
        return False


def check_for_update(base_url):
    """Main OTA update routine."""
    if not should_check_ota():
        logging.info("[OTA] Skipping OTA — last check still valid.")
        return

    try:
        logging.info("[OTA] Checking for new firmware at %s", base_url)
        r = urequests.get(base_url + "/latest.json")
        if r.status_code != 200:
            logging.error("[OTA] Failed to fetch version info — HTTP %s", r.status_code)
            return

        data = r.json()
        r.close()

        version = data.get("version")
        url = data.get("url")

        if not version or not url:
            logging.error("[OTA] Invalid response — missing version or URL.")
            return

        # Load current version if available
        current_version = None
        try:
            with open("/data/version.txt", "r") as f:
                current_version = f.read().strip()
        except Exception:
            logging.warning("[OTA] No current version file found.")

        if current_version == version:
            logging.info("[OTA] Firmware is already up to date (version %s).", version)
            _write_last_check()
            return

        logging.info("[OTA] New firmware found — current: %s, available: %s", current_version, version)

        if download_update(url):
            apply_update()
        else:
            logging.error("[OTA] Download failed — skipping update.")
            _write_last_check()

    except Exception as e:
        logging.error("[OTA] Exception during update check: %s", e)
        _write_last_check()
