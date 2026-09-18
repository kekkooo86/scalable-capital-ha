# Scalable Capital for Home Assistant

Read-only Home Assistant integration + add-on that brings your **Scalable
Capital** portfolio into Home Assistant: total value, securities, cash and
plus/minus performance (today, week, month, year, total).

No trading is exposed — everything is read-only.

> **Unofficial.** Not affiliated with, endorsed by or supported by Scalable
> Capital GmbH. "Scalable" and the Scalable logo are trademarks of Scalable
> Capital GmbH. See [NOTICE](NOTICE).

---

## Components

| Path | What it is |
|---|---|
| [`scalable_cli_bridge/`](scalable_cli_bridge) | Home Assistant add-on. Runs the official `sc` CLI inside a Debian container and exposes a read-only HTTP API plus a device-code login panel. |
| [`custom_components/scalable_capital/`](custom_components/scalable_capital) | Home Assistant custom integration. Auto-detects the add-on and creates the sensors. |
| [`dashboard/`](dashboard) | Example app-like Lovelace dashboard + the helper package it relies on. |

## Why an add-on?

The official `sc` CLI is a **glibc** binary, while the Home Assistant Core
container is Alpine/musl (`gcompat` is not enough). The add-on runs `sc` in a
Debian (`trixie`) container managed by Home Assistant and exposes it over the
internal Docker network only (no LAN port mapping; the login panel is reached
through authenticated Ingress).

## Requirements

- Home Assistant OS / Supervised, `amd64` or `aarch64`
- A Scalable Capital account with **Profile → Security → Agentic Investing**
  enabled

## Installation

### 1 · Add-on

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add `https://github.com/kekkooo86/scalable-capital-ha`
3. Install **Scalable CLI Bridge** and **Start** it.
4. Open its panel (**Scalable** in the sidebar) and press **Accedi / Log in**.
   Confirm the URL + device code in the Scalable app or website.

Session data is persisted in the add-on's `/data`, so the login survives
restarts.

### 2 · Integration

1. Copy `custom_components/scalable_capital/` into your `/config/custom_components/`
   folder — or add this repository to **HACS** as a custom repository with
   category *Integration*.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → Scalable Capital**.
   Leave the URL field empty to auto-detect the add-on; fill it in only if
   auto-detection fails (e.g. custom hostname). Expected:
   `http://scalable-cli-bridge:8788` (or `http://local-scalable-cli-bridge:8788`
   for local installs).

### 3 · Example dashboard (optional)

1. Copy [`dashboard/scalable_pl_helpers.yaml`](dashboard/scalable_pl_helpers.yaml)
   into `/config/packages/` and make sure packages are enabled:

   ```yaml
   # configuration.yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

   Restart Home Assistant.
2. Create a new dashboard, open **Raw configuration editor** and paste
   [`dashboard/scalable_dashboard.yaml`](dashboard/scalable_dashboard.yaml).
3. The dashboard uses these HACS frontend cards:
   `apexcharts-card`, `button-card`, `card-mod`, `layout-card`.

## Sensors

| Entity | Description |
|---|---|
| `sensor.scalable_capital_portafoglio_scalable` | Total portfolio value (€) |
| `sensor.scalable_capital_titoli_scalable` | Securities value (€) |
| `sensor.scalable_capital_cash_scalable` | Cash (€) |
| `sensor.scalable_capital_plus_minusvalenza_oggi` | P/L today (€) |
| `sensor.scalable_capital_plus_minusvalenza_settimana` | P/L this week (€) |
| `sensor.scalable_capital_plus_minusvalenza_mese` | P/L this month (€) |
| `sensor.scalable_capital_plus_minusvalenza_anno` | P/L this year (€) |
| `sensor.scalable_capital_plus_minusvalenza_totale` | P/L since inception (€) |
| `sensor.scalable_capital_ultimo_aggiornamento_portafoglio` | Last valuation timestamp |
| `binary_sensor.scalable_capital_sc_bridge_online` | Bridge/session reachability |

The smooth-P/L helper package additionally creates:
`sensor.scalable_capital_pl_intraday`, `..._pl_settimana`, `..._pl_mese`,
`..._pl_anno` (see the comments in the package).

## Options

- **Add-on option `scan_interval`** (300–86400 s, default 900): the polling
  interval. When set, it takes precedence over the integration option.
- **Integration options**: bridge URL override (advanced) and a fallback
  polling interval.

## API exposed by the add-on

Internal network only, port `8788`:

`GET /health` · `GET /config` · `GET /session` · `GET /portfolio` ·
`GET /quote?isin=…` · `POST /login/start` · `GET /login/status` · `POST /logout`

## Troubleshooting

- **Sensors `unavailable`** → the session expired: open the add-on panel and
  log in again.
- **`sc` session lock**: the CLI holds a session lock during login, so while a
  login is in progress other calls are blocked and the integration may briefly
  go `unavailable`. This is expected.
- **Config flow cannot find the add-on** → enter the bridge URL manually in the
  integration setup (e.g. `http://<addon-hostname>:8788`).

## Notes

- Some entity names and the add-on UI are in **Italian**.
- The default polling interval is conservative to avoid hitting the broker
  needlessly.

## License

[MIT](LICENSE). Third-party assets and trademarks are covered in
[NOTICE](NOTICE).
