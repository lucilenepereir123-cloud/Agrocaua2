# API_PAP
API que recebe dados de sensores e ESP32-CAM


Estrutura exemplar dos dados:

{
  "device_id": "SENSOR_001",
  "timestamp": "2026-02-14T10:30:45.123456",
  "gps": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "bme280": {
    "temperatura": 24.5,
    "humidade": 65.3,
    "pressao": 1013.25
  },
  "solo": {
    "humidade": 45.2
  },
  "vibracao": {
    "detectada": false
  },
  "visao": {
    "detecao_praga": true,
    "tipo_praga": "Afídeo",
    "confianca": 0.92
  }
}
```



## Endpoints da API
```

---

### GET https://api-pap-dqtp.onrender.com/dados_sensores
Retorna os últimos 10 registros de todos os sensores.


### GET https://api-pap-dqtp.onrender.com/api/gps
Retorna o registro mais recente do sensor GPS.



---

### GET https://api-pap-dqtp.onrender.com/api/bme280
Retorna o registro mais recente do sensor BME280 (temperatura, humidade e pressão do ar).


---

### GET https://api-pap-dqtp.onrender.com/api/solo
Retorna o registro mais recente de humidade do solo.



---

### GET https://api-pap-dqtp.onrender.com/api/vibracao
Retorna o registro mais recente de vibração.


---

### GET https://api-pap-dqtp.onrender.com/api/localizacao
Retorna o registro mais recente de localização.



---

### GET https://api-pap-dqtp.onrender.com/api/visao
Retorna o registro mais recente de detecção de pragas.

