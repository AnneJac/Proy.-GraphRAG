import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def get_driver():
    uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD no está definido.")

    return GraphDatabase.driver(uri, auth=(user, password))