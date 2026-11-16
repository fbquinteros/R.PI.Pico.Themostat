# WiFi Configuration REST API

When the Raspberry Pi Pico W cannot connect to its configured WiFi network, it enters Access Point (AP) mode and starts a built-in HTTP server that accepts WiFi credentials via a REST API.

## How It Works

1. **Device boots** - Tries to connect to WiFi using credentials from `config.py` or saved config file
2. **Connection fails** - Device starts AP mode with SSID `rpi_temp_XXXX` (where XXXX is device-specific)
3. **HTTP server starts** - Listens on `http://192.168.4.1:80` for configuration requests
4. **User sends credentials** - POST JSON with WiFi SSID and password
5. **Credentials saved** - Stored in `wifi_config.json` on device flash
6. **Device reconnects** - Attempts to join the specified WiFi network
7. **Reboot** - On success, device reboots and joins the network permanently

## API Endpoint

### POST `/api/wifi`

Send WiFi credentials to configure the device.

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "ssid": "your_wifi_network_name",
  "password": "your_wifi_password"
}
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "WiFi credentials saved, attempting connection...",
  "ssid": "your_wifi_network_name"
}
```

**Error Responses:**

- **400 Bad Request** - Missing ssid or password, or invalid JSON
- **404 Not Found** - Wrong endpoint
- **500 Internal Server Error** - Server error

## Usage Examples

### Using curl

```bash
curl -X POST http://192.168.4.1/api/wifi \
  -H "Content-Type: application/json" \
  -d '{"ssid":"MyHomeWiFi","password":"MySecretPassword"}'
```

### Using Python requests

```python
import requests

response = requests.post(
    'http://192.168.4.1/api/wifi',
    headers={'Content-Type': 'application/json'},
    json={
        'ssid': 'MyHomeWiFi',
        'password': 'MySecretPassword'
    }
)

print(response.json())
```

### Using a Web Browser (simple test)

You can also test with a simple HTML page:

```html
<form action="http://192.168.4.1/api/wifi" method="POST">
  <input type="text" name="ssid" placeholder="WiFi SSID">
  <input type="password" name="password" placeholder="WiFi Password">
  <button type="submit">Configure WiFi</button>
</form>
```

## AP Mode Details

- **AP SSID**: `rpi_temp_XXXX` (unique per device)
- **AP Password**: `First,Connect,Setup`
- **AP IP Address**: `192.168.4.1`
- **API Port**: 80

## Workflow

```
┌─────────────────┐
│ Device Boots    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Try WiFi        │
│ Connection      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
  Success   Failed
    │         │
    v         v
┌───────────┐  ┌──────────────────┐
│ Normal    │  │ AP Mode          │
│ Operation │  │ + HTTP Server    │
└───────────┘  └────────┬─────────┘
                        │
                        v
                 ┌──────────────┐
                 │ User sends   │
                 │ POST /api/wifi│
                 └──────┬───────┘
                        │
                        v
                 ┌──────────────┐
                 │ Credentials  │
                 │ Saved        │
                 └──────┬───────┘
                        │
                        v
                 ┌──────────────┐
                 │ Connect to   │
                 │ WiFi         │
                 └──────┬───────┘
                        │
                  ┌─────┴─────┐
                  │           │
                Success     Failed
                  │           │
                  v           v
            ┌─────────┐  ┌──────────────┐
            │ Reboot  │  │ Retry AP +   │
            │ & Join  │  │ HTTP Server  │
            └─────────┘  └──────────────┘
```

## Files

- **`config.py`** - Default WiFi credentials (never commit to git)
- **`wifi_config.json`** - Saved credentials on device flash (never commit to git)
- **`main.py`** - Main firmware with HTTP server implementation

## Security Notes

- The API is only accessible when the device is in AP mode (not connected to WiFi)
- Credentials are saved in plaintext on flash storage
- For production use, consider adding authentication to the API endpoint
