import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import text
import tomlkit

CONFIG_PATH = "/home/ocs/python/security/WeatherSafety/db_config.toml"

def get_db_url() -> str:
    with open(CONFIG_PATH, "r") as config_fp:
        config_doc = tomlkit.load(config_fp)

        db_host = config_doc["database"]["host"]

        db_user = config_doc["database"]["user"]
        db_password = config_doc["database"]["password"]

        db_name = config_doc["database"]["name"]

        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}/{db_name}"
    

if __name__ == "__main__":
    url = get_db_url()
    
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * \
                                   FROM sensors.arduino_in \
                                   ORDER BY tstamp DESC \
                                   LIMIT 10;"))
        
        for row in result:
            print(row)