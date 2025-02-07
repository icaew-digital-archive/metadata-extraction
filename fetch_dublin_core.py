import requests
from bs4 import BeautifulSoup
from config import log_message

def fetch_dublin_core_definitions():
    urls = {
        "Dublin Core Elements": "https://www.dublincore.org/specifications/dublin-core/dces/",
        "Format": "https://www.iana.org/assignments/media-types/media-types.xhtml",
        "Date": "https://www.w3.org/TR/NOTE-datetime",
        "Type": "https://www.dublincore.org/specifications/dublin-core/dcmi-type-vocabulary/",
        "Language": "https://www.loc.gov/standards/iso639-2/php/code_list.php"
    }
    definitions = {}

    for key, url in urls.items():
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            definitions[key] = BeautifulSoup(response.text, 'html.parser').get_text(separator="\n", strip=True)[:5000]
        except requests.RequestException as e:
            log_message(f"Error fetching {key} from {url}: {e}")

    return definitions
