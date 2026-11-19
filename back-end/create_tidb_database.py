"""Create the application's database on TiDB using credentials from .env."""

import os
import ssl

import pymysql
from dotenv import load_dotenv
from sqlalchemy.engine import make_url


load_dotenv()
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL não está configurada no arquivo .env")

url = make_url(database_url)
if url.drivername != "mysql+pymysql":
    raise SystemExit("DATABASE_URL precisa usar mysql+pymysql para conectar ao TiDB")

ssl_ca = url.query.get("ssl_ca")
if not ssl_ca:
    raise SystemExit("A URL precisa informar o certificado em ssl_ca")

connection = pymysql.connect(
    host=url.host,
    port=url.port or 4000,
    user=url.username,
    password=url.password,
    database="sys",
    ssl_ca=ssl_ca,
    ssl_verify_cert=True,
    ssl_verify_identity=True,
    connect_timeout=20,
)

try:
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS `pousada_db`")
    connection.commit()
    print("Banco pousada_db criado ou já existente.")
finally:
    connection.close()
