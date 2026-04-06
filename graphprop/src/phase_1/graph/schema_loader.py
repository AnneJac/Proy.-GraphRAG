from src.phase_1.graph.connection import get_driver


def _merge_list_nodes(tx, label: str, values: list[str]):
    query = f"""
    UNWIND $values AS value
    MERGE (n:{label} {{name: value}})
    """
    tx.run(query, values=values)


def _link_bank_project(tx, banks: list[str], projects: list[str]):
    if not banks or not projects:
        return

    query = """
    UNWIND $banks AS bank
    UNWIND $projects AS project
    MERGE (b:BankEntity {name: bank})
    MERGE (p:ProjectEntity {name: project})
    MERGE (b)-[:HAS_PROJECT]->(p)
    """
    tx.run(query, banks=banks, projects=projects)


def _link_project_status(tx, projects: list[str], statuses: list[str]):
    if not projects or not statuses:
        return

    query = """
    UNWIND $projects AS project
    UNWIND $statuses AS status
    MERGE (p:ProjectEntity {name: project})
    MERGE (s:ProjectStatus {name: status})
    MERGE (p)-[:HAS_STATUS]->(s)
    """
    tx.run(query, projects=projects, statuses=statuses)


def _link_project_events(tx, projects: list[str], events: list[str]):
    if not projects or not events:
        return

    query = """
    UNWIND $projects AS project
    UNWIND $events AS event
    MERGE (p:ProjectEntity {name: project})
    MERGE (e:EvolutionEvent {name: event})
    MERGE (p)-[:HAS_EVOLUTION_EVENT]->(e)
    """
    tx.run(query, projects=projects, events=events)


def _link_people_roles(tx, people: list[str], roles: list[str]):
    if not people or not roles:
        return

    query = """
    UNWIND $people AS person
    UNWIND $roles AS role
    MERGE (p:PersonnelEntity {name: person})
    MERGE (r:PersonnelRole {name: role})
    MERGE (p)-[:HAS_ROLE]->(r)
    """
    tx.run(query, people=people, roles=roles)


def _link_project_people(tx, projects: list[str], people: list[str]):
    if not projects or not people:
        return

    query = """
    UNWIND $projects AS project
    UNWIND $people AS person
    MERGE (pr:ProjectEntity {name: project})
    MERGE (pe:PersonnelEntity {name: person})
    MERGE (pr)-[:HAS_PERSONNEL]->(pe)
    """
    tx.run(query, projects=projects, people=people)


def _link_bank_profiles(tx, banks: list[str], profiles: list[str]):
    if not banks or not profiles:
        return

    query = """
    UNWIND $banks AS bank
    UNWIND $profiles AS profile
    MERGE (b:BankEntity {name: bank})
    MERGE (bp:BankProfile {name: profile})
    MERGE (b)-[:HAS_PROFILE]->(bp)
    """
    tx.run(query, banks=banks, profiles=profiles)


def _link_document_source(tx, docs: list[str], projects: list[str]):
    if not docs:
        return

    query = """
    UNWIND $docs AS doc
    MERGE (d:SourceDocument {name: doc})
    """
    tx.run(query, docs=docs)

    if projects:
        query2 = """
        UNWIND $docs AS doc
        UNWIND $projects AS project
        MERGE (d:SourceDocument {name: doc})
        MERGE (p:ProjectEntity {name: project})
        MERGE (d)-[:DESCRIBES_PROJECT]->(p)
        """
        tx.run(query2, docs=docs, projects=projects)


def save_structured_graph(entities: dict) -> None:
    """
    Save structured graph entities and relationships into Neo4j.
    """
    banks = entities.get("BankEntity", [])
    profiles = entities.get("BankProfile", [])
    events = entities.get("EvolutionEvent", [])
    people = entities.get("PersonnelEntity", [])
    roles = entities.get("PersonnelRole", [])
    projects = entities.get("ProjectEntity", [])
    statuses = entities.get("ProjectStatus", [])
    docs = entities.get("SourceDocument", [])

    driver = get_driver()

    with driver.session() as session:
        session.execute_write(_merge_list_nodes, "BankEntity", banks)
        session.execute_write(_merge_list_nodes, "BankProfile", profiles)
        session.execute_write(_merge_list_nodes, "EvolutionEvent", events)
        session.execute_write(_merge_list_nodes, "PersonnelEntity", people)
        session.execute_write(_merge_list_nodes, "PersonnelRole", roles)
        session.execute_write(_merge_list_nodes, "ProjectEntity", projects)
        session.execute_write(_merge_list_nodes, "ProjectStatus", statuses)
        session.execute_write(_merge_list_nodes, "SourceDocument", docs)

        session.execute_write(_link_bank_project, banks, projects)
        session.execute_write(_link_bank_profiles, banks, profiles)
        session.execute_write(_link_project_status, projects, statuses)
        session.execute_write(_link_project_events, projects, events)
        session.execute_write(_link_people_roles, people, roles)
        session.execute_write(_link_project_people, projects, people)
        session.execute_write(_link_document_source, docs, projects)

    driver.close()