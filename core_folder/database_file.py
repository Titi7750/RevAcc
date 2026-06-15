# Import Python packages
import os
from pathlib import Path

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Import personal functions
## None

# Custom variable type construction
## None

# -----

# Chemin absolu vers .env.local (indépendant du répertoire de lancement)
load_dotenv(Path(__file__).parent.parent / ".env.local")
_ENGINE = None

# -----

def get_engine_method():
    """ Get the SQLAlchemy engine for the database connection """

    global _ENGINE
    if _ENGINE is None:
        user     = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        host     = os.getenv("DB_HOST", "localhost")
        port     = os.getenv("DB_PORT", "3306")
        name     = os.getenv("DB_NAME", "rev_acc_database")
        _ENGINE = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}",
            pool_pre_ping=True,
            pool_recycle=3600,
        )

    return _ENGINE

# -----

def get_connection_method():
    """ Get a connection to the database """

    return get_engine_method().connect()

# Alias utilisé par les modules
get_connection = get_connection_method
