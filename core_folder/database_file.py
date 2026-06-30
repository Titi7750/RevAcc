# Import Python packages
import os
from pathlib import Path

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Import personal functions
## None

# Custom variable type construction
## None

# -----

# Chemin absolu vers .env.local (indépendant du répertoire de lancement)
load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
_ENGINE = None

# -----

def get_engine_method():
    """ Get the SQLAlchemy engine for the database connection """

    global _ENGINE
    # On crée le moteur une seule fois, puis on le réutilise à chaque appel (pattern singleton)
    if _ENGINE is None:
        user     = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        host     = os.getenv("DB_HOST", "localhost")
        port     = os.getenv("DB_PORT", "3306")
        name     = os.getenv("DB_NAME", "rev_acc_database")
        _ENGINE = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}",
            pool_pre_ping=True, # vérifie que la connexion est toujours active avant de l'utiliser
            pool_recycle=3600,  # renouvelle les connexions inactives après 1h (évite les timeouts MySQL)
        )

    return _ENGINE

# -----

def get_connection_method():
    """ Get a connection to the database """

    return get_engine_method().connect()

# Alias utilisé par les modules
get_connection = get_connection_method

# -----

def get_or_create(param_connection, param_table: str, param_column_name: str, param_value: str | None) -> int | None:
    """ Retourne l'ID associé à une valeur, crée la ligne si elle n'existe pas """

    if param_value is None:
        return None

    id_column = f"id_{param_table}"

    row = param_connection.execute(
        text(f"SELECT {id_column} FROM `{param_table}` WHERE `{param_column_name}` = :value"),
        {"value": param_value}
    ).fetchone()

    # Si elle existe, on retourne son ID sans rien créer
    if row:
        return int(row[0])

    # Sinon on l'insère et on retourne l'ID de la nouvelle ligne
    result = param_connection.execute(
        text(f"INSERT INTO `{param_table}` (`{param_column_name}`) VALUES (:value)"),
        {"value": param_value},
    )
    param_connection.commit()

    return int(result.lastrowid)

# -----

def get_or_create_many(param_connection, param_table: str, param_column_name: str, param_values) -> dict:
    """ Applique get_or_create aux valeurs uniques valides, retourne un dictionnaire {value: id} """

    # On dédoublonne d'abord pour n'appeler get_or_create qu'une fois par valeur distincte
    # (ex : si 500 transactions ont le même distributeur, on ne fait qu'un seul SELECT/INSERT)
    unique_values = {value for value in param_values if value is not None and str(value) not in ("", "nan")}

    return {value: get_or_create(param_connection, param_table, param_column_name, value) for value in unique_values}
