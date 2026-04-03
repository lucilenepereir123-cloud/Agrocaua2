import requests

url = "https://sua-api-url-aqui.com/endpoint"  # Substitua pela URL correta

try:
    consumo = requests.get(url)
    
    print(f"Status Code: {consumo.status_code}")
    print(f"Headers: {dict(consumo.headers)}")
    print(f"Conteúdo (primeiros 500 chars):\n{consumo.text[:500]}")
    
    if consumo.status_code == 200:
        if consumo.text.strip():  # Verifica se não está vazio
            if consumo.headers.get('content-type', '').startswith('application/json'):
                dados = consumo.json()
                print("JSON carregado com sucesso!")
            else:
                print(f"Content-Type não é JSON: {consumo.headers.get('content-type')}")
        else:
            print("Resposta vazia")
    else:
        print("Erro na API")
        
except requests.exceptions.RequestException as e:
    print(f"Erro de conexão: {e}")
except Exception as e:
    print(f"Erro inesperado: {e}")

headers = {
    'Authorization': 'Bearer SEU_TOKEN',
    'Content-Type': 'application/json'
}
consumo = requests.get(url, headers=headers)