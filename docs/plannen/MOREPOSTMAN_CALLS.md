# Calls-overzicht voor morepostman — talk-with-the-engineer (vuistregels)

Elk rekengereedschap is op twee manieren aanroepbaar: als REST-endpoint en als MCP-tool.
Beide routes draaien op dezelfde server en gebruiken exact dezelfde invoervelden; alleen de
verpakking verschilt. Alles hieronder is geverifieerd tegen de TEST-omgeving.

## Basis-URL's

| Omgeving | Basis-URL |
|---|---|
| TEST | `https://talk-with-the-engineer-test.hkvservices.nl` |

- OpenAPI-spec (alle REST-schema's en voorbeelden): `GET {base}/openapi.json`
- Swagger UI (handmatig proberen): `{base}/docs`
- MCP-endpoint (streamable HTTP, stateless): `POST {base}/mcp/vuistregels/`

## REST-conventies

- Alle tools zijn `POST {base}/tools.RulesOfThumb/<endpoint>` met `Content-Type: application/json`.
- De body is het invoermodel zelf (geen wrapper): zie de voorbeeldbody's hieronder.
- Antwoord: `200` met JSON `{data, description, status?, assumptions?, ...}`.
- Ongeldige invoer: `422` met `{"detail": [{"type": ..., "msg": ...}]}` — het bericht legt uit
  welke waarden wél geldig zijn. Domeinfouten (via `ModelRetry`/`ToolError`) komen als
  `{"type": "model_retry"}` in dezelfde vorm terug.
- Velden die je niet weet: **weglaten**, niet schatten. De tool vult dan een aanname in en
  meldt dat in `assumptions`.

## MCP-conventies

- Endpoint: `POST {base}/mcp/vuistregels/` — JSON-RPC 2.0 over streamable HTTP.
- Verplichte headers: `Content-Type: application/json` en
  `Accept: application/json, text/event-stream` (anders `406`).
- Server is stateless: geen `initialize`-handshake of sessie-header nodig; `tools/list` en
  `tools/call` werken direct.
- Antwoorden zijn SSE-geframed (`event: message` / `data: {...}`); de JSON zit achter het
  `data: `-prefix.
- Toolschema's uitlezen: `{"jsonrpc":"2.0","id":1,"method":"tools/list"}` — per tool zit de
  JSON Schema in `result.tools[].inputSchema`.
- Tool aanroepen: `tools/call` met `params.name` = MCP-toolnaam en `params.arguments` =
  `{"input": <REST-body>}`. De REST-body en `arguments.input` zijn identiek.
- Toolfouten komen bij MCP niet als HTTP-fout maar als `result.isError: true` met het
  bericht in `result.content`.

### Voorbeeld tools/list

```bash
curl -s -X POST {base}/mcp/vuistregels/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | sed -n 's/^data: //p' | jq '.result.tools[] | {name, inputSchema}'
```

### Voorbeeld tools/call (zelfde som als het REST-voorbeeld hieronder)

```bash
curl -s -X POST {base}/mcp/vuistregels/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"calculate_retention_given_h","arguments":{"input":{"area_ha":4000,"discharge_capacity_m3_per_sec":5,"return_period":100,"delta_h_available":1.0}}}}' \
  | sed -n 's/^data: //p' | jq
```

### Voorbeeld REST

```bash
curl -s -X POST {base}/tools.RulesOfThumb/retention_given_h \
  -H "Content-Type: application/json" \
  -d '{"area_ha":4000,"discharge_capacity_m3_per_sec":5,"return_period":100,"delta_h_available":1.0}'
```

## De elf tools

Per tool: het REST-pad, de MCP-toolnaam en een werkende voorbeeldbody (afkomstig uit de
OpenAPI-spec). De voorbeeldbody is bij REST de hele request-body en bij MCP de waarde van
`arguments.input`.

### 1. read_me — de handleiding van de toolset

- REST: `POST /tools.RulesOfThumb/read_me`
- MCP: `read_me`

```json
{"modules": ["terugkoppelen"]}
```

Modules: `bronnen`, `vuistregels`, `gebruik`, `terugkoppelen`; zonder `modules` een korte index.

### 2. retention_given_h — vasthouden, gegeven peilstijging

- REST: `POST /tools.RulesOfThumb/retention_given_h`
- MCP: `calculate_retention_given_h`

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "delta_h_available": 1.0}
```

### 3. retention_given_area — vasthouden, gegeven areaal

- REST: `POST /tools.RulesOfThumb/retention_given_area`
- MCP: `calculate_retention_given_area`

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "delta_area_ha": 1158}
```

### 4. store_given_h — bergen, gegeven peilstijging

- REST: `POST /tools.RulesOfThumb/store_given_h`
- MCP: `calculate_store_given_h`

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "delta_h_available": 1.0}
```

### 5. store_given_area — bergen, gegeven open-wateroppervlak

- REST: `POST /tools.RulesOfThumb/store_given_area`
- MCP: `calculate_store_given_area`

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "area_available_ha": 200}
```

### 6. discharge_given_h — afvoeren, gegeven peilstijging

- REST: `POST /tools.RulesOfThumb/discharge_given_h`
- MCP: `calculate_discharge_given_h`

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "delta_h_available": 1.0}
```

### 7. discharge_given_discharge — afvoeren, gegeven extra gemaalcapaciteit

- REST: `POST /tools.RulesOfThumb/discharge_given_discharge`
- MCP: `calculate_discharge_given_discharge`

```json
{"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100, "delta_discharge_capacity_m3_per_sec": 2.5}
```

### 8. supply_given_h — aanvoeren, gegeven toelaatbare uitzakking

- REST: `POST /tools.RulesOfThumb/supply_given_h`
- MCP: `calculate_supply_given_h`

```json
{"area_ha": 4000, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3}
```

### 9. supply_given_supply — aanvoeren, gegeven inlaatcapaciteit

- REST: `POST /tools.RulesOfThumb/supply_given_supply`
- MCP: `calculate_supply_given_supply`

```json
{"area_ha": 4000, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3, "delta_supply_capacity_l_s_ha": 0.4}
```

### 10. cascade_given_excess — systeemvraag bij wateroverschot

- REST: `POST /tools.RulesOfThumb/cascade_given_excess`
- MCP: `calculate_cascade_given_excess`

```json
{
  "return_period": 100,
  "nodes": [
    {"name": "polder A", "area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "percentage_open_water": 3.5, "drains_to": "boezem"},
    {"name": "boezem", "area_ha": 8000, "discharge_capacity_m3_per_sec": 10, "percentage_open_water": 3.5}
  ]
}
```

### 11. allocation_given_shortage — systeemvraag bij watertekort (verdringingsreeks)

- REST: `POST /tools.RulesOfThumb/allocation_given_shortage`
- MCP: `calculate_allocation_given_shortage`

```json
{
  "available_source_volume_m3": 4000000,
  "nodes": [
    {"name": "landbouwpolder", "area_ha": 4000, "category": 4, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3, "intake_capacity_m3_per_sec": 1.5, "percentage_open_water": 3.5, "draws_from": "boezem"},
    {"name": "boezem", "area_ha": 8000, "category": 4, "deficit_mm_per_day": 0, "drawdown_available_m": 0.3, "intake_capacity_m3_per_sec": 10.0, "percentage_open_water": 3.5}
  ]
}
```

## Aandachtspunten voor de testtool

- **Pariteitstest**: dezelfde invoer via REST en via MCP (`arguments.input`) moet hetzelfde
  rekenresultaat geven; dat is een zinvolle automatische check per tool.
- **Negatieve test REST**: een ongeldige waarde (bijv. `return_period: -1`) moet een `422`
  geven met leesbare uitleg in `detail[].msg` — geen `500`.
- **Negatieve test MCP**: dezelfde ongeldige waarde moet een JSON-RPC-antwoord geven met
  `result.isError: true` (HTTP blijft `200`).
- **Schemabron**: REST-schema's uit `{base}/openapi.json`; MCP-schema's uit `tools/list`
  (`result.tools[].inputSchema`). Die twee horen inhoudelijk overeen te komen.
- Antwoorden bevatten soms een `status`-veld; de handleiding (`read_me`, module
  `terugkoppelen`) beschrijft wat je niet mag rapporteren zonder `status` te controleren.
