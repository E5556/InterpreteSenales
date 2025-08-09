import requests
import json

API_URL = "https://restcountries.com/v3.1/all?fields=name"

def get_countries():
    """
    Obtiene una lista de nombres de países desde la API de REST Countries.
    Retorna una lista ordenada de nombres de países o una lista vacía si falla.
    """
    try:
        response = requests.get(API_URL, timeout=10)
        # Lanza una excepción si la respuesta no es exitosa (ej. 404, 500)
        response.raise_for_status()
        
        countries_data = response.json()
        
        # Extraemos el nombre común de cada país
        country_names = [country['name']['common'] for country in countries_data]
        
        # Ordenamos la lista alfabéticamente
        country_names.sort()
        
        return country_names

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API de países: {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error al procesar la respuesta de la API de países: {e}")
        return []

# Para probar el módulo de forma independiente
if __name__ == '__main__':
    print("Obteniendo lista de países...")
    countries = get_countries()
    
    if countries:
        print(f"Se encontraron {len(countries)} países.")
        # Imprime los primeros 10 para verificar
        print("Ejemplos:", countries[:10])
    else:
        print("No se pudo obtener la lista de países.") 