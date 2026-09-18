"""Constants for the Scalable Capital integration."""

from homeassistant.const import Platform

DOMAIN = "scalable_capital"

CONF_URL = "url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8788

# Hostname dell'add-on: dipende da come è installato (locale `local_<slug>` o
# da repository `<slug>`). L'integrazione li prova in ordine e usa il primo
# che risponde su /health.
BRIDGE_HOSTS = (
    "local-scalable-cli-bridge",
    "scalable-cli-bridge",
    "local_scalable_cli_bridge",
    "scalable_cli_bridge",
)
DEFAULT_URL = f"http://{BRIDGE_HOSTS[0]}:{DEFAULT_PORT}"
DEFAULT_SCAN_INTERVAL = 900
MIN_SCAN_INTERVAL = 300

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

BRIDGE_PERFORMANCE_TIMEFRAMES = {
    "INTRADAY": "today",
    "ONE_WEEK": "week",
    "ONE_MONTH": "month",
    "ONE_YEAR": "year",
    "MAX": "total",
}