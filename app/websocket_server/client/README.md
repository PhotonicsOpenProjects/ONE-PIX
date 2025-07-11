# 📡 OnePixClient – WebSocket Python Client

`OnePixClient` is a lightweight Python class designed to interact with theONE-PIX WebSocket (Socket.IO) server. It enables sending instructions, updating configuration parameters, and triggering measurements through asynchronous events.

---

## 🔧 Features

- Connect/disconnect to/from a WebSocket server
- Update a parameter via `update_param`
- Read a parameter via `get_param`
- Trigger a measurement via `mesure`
- Handle server events:
  - `config_updated`
  - `config_data`
  - `mesure`
  - `erreur`
  - `param_data`

---

## 🧪 Example Usage

```python
from client import OnePixClient  # Make sure your file is named client.py

client = OnePixClient(server_url="http://localhost:5000")

client.connect()

# Change a parameter
result = client.change_param("exposure", "150")
print("Updated parameter:", result)

# Read a parameter
value = client.read_param("exposure")
print("Current value:", value)

# Run a measurement
mesure_data = client.run_measure()
print("Measured data:", mesure_data)

client.disconnect()
```

---

## 📦 Dependencies

Install the required library:

```bash
pip install "python-socketio[client]"
```

---

## ⏱️ Configuration

- `server_url` *(str)*: WebSocket server URL (default: `http://localhost:5000`)
- `timeout` *(int)*: Timeout in seconds for server responses (default: `10`)

---

## ⚠️ Error Handling

If the server emits an `erreur` event, a `RuntimeError` is raised with the message received from the server.

---

## 📁 Emitted Instructions

### `update_param`
```json
{
  "action": "update_param",
  "key": "parameter_name",
  "value": "value"
}
```

### `get_param`
```json
{
  "action": "get_param",
  "key": "parameter_name"
}
```

### `mesure`
```json
{
  "action": "mesure"
}
```

---


## 📬 Server Events Handled

These events are emitted by the server based on the received `instruction`.


- `config_updated`: Emitted when a parameter is successfully updated. Contains the updated key, value, and config file.
- `param_data`: Emitted when a parameter is read successfully. Contains the key, value, and config filename.
- `mesure`: Contains a hypercube (`reconstructed_image`), a list of `wavelengths`, and a `rgb_img` preview.
- `erreur`: Emitted on any failure (missing key, type conversion error, file I/O issue, etc.). Contains a `message` field.


---

## 🛠️ Modifiable Parameters (`update_param`)

The method `change_param(key, value)` allows dynamic modification of system settings. All parameters are **sent as string values**, and **type conversion is handled server-side**.

---

### 📋 List of Available Parameters

#### 🔬 Imaging Parameters

| Parameter         | Example Value   | Description                           |
|-------------------|------------------|---------------------------------------|
| `imaging_method`  | `"FourierSplit"` | Imaging method used                   |
| `spatial_res`     | `"3"`            | Spatial resolution of the datacube    |
| `Normalisation`   | `"false"`        | Enable/disable normalization          |
| `dynamic_tint`    | `"false"`        | Enable/disable search of optimal tint  |

#### 📷 Camera / Spectrometer Parameters

| Parameter              | Example Value    | Description                            |
|------------------------|------------------|----------------------------------------|
| `name_spectro`         | `"Stub"`         | Spectrometer name used in ONE-PIX      |
| `name_camera`          | `"Stub"`         | Camera name used in ONE-PIX            |
| `integration_time_ms`  | `"2.0"`          | Integration time (ms)                  |
| `height`               | `"600"`          | height pattern window resolution       |
| `width`                | `"800"`          |  width pattern  window resolution |
| `wl_lim`               | `"[350,800]"`    | Wavelength range (JSON string)         |
| `spectro_scans2avg`    | `"1"`            | Number of scans to average for oen pattern measure  |
| `proj_position`        | `"auto"`         | Projector position                     |

#### 🧠 Advanced / Calibration Parameters

| Parameter              | Example Value                      | Description                          |
|------------------------|-------------------------------------|--------------------------------------|
| `m`                    | `[[...], [...], [...]]` (JSON str)  | 3x3 corregistration calibration matrix  |
| `clustering_method`    | `"Kmeans"`                          | Clustering method   for HAS measures  |
| `clustering_parameters`| `"[2,5]"`                           | Clustering parameters (JSON string)  |
| `max_height`           | `"463"`                             | Max processing height                |
| `max_width`            | `"525"`                             | Max processing width                 |
| `IP`                   | `"ws://192.168.5.60:8000"`          | WebSocket server IP                  |
| `port`                 | `"8000"`                            | Server port                          |
| `mode_choice`          | `"Advanced"`                        | Selected operating mode              |
| `acquisition_method`   | `"Complete"`                        | Acquisition method                   |
| `normalisation_path`   | `""`                                | Path to normalization file (optional)|

---

### 🔧 Parameter Update Example

```python
client.change_param("integration_time_ms", "10")
client.change_param("clustering_parameters", "[2, 4]")
client.change_param("Normalisation", "true")
```

> ⚠️ Complex types such as lists and matrices must be passed as **JSON strings** (`"[...]"`, `"[[...]]"`).

---

## 🧑‍💻 Author

Developed by [Garussias] – Feel free to open an issue for questions or suggestions.