from src.database.models import get_session
from src.database.repository import (
    get_all_banks,
    get_all_projects,
    get_all_personnel,
    get_all_regulations,
    get_bank_profile,
)
from src.graph.connection import get_driver


def build_master_kg():
    session = get_session()
    driver = get_driver()

    with driver.session() as neo:

        # BANKS
        for b in get_all_banks(session):
            neo.run("""
                MERGE (b:BankEntity {bank_id: $bank_id})
                SET b.name = $name,
                    b.country = $country,
                    b.tier = $tier,
                    b.total_assets_usd = $assets,
                    b.founded_year = $founded_year
            """,
            bank_id=b.bank_id,
            name=b.name,
            country=b.country,
            tier=b.tier,
            assets=b.total_assets_usd,
            founded_year=b.founded_year)

        # PROJECTS
        for p in get_all_projects(session):
            neo.run("""
                MERGE (p:ProjectEntity {project_id: $project_id})
                SET p.name = $name,
                    p.description = $description,
                    p.status = $status,
                    p.budget_usd = $budget,
                    p.start_date = toString($start_date),
                    p.end_date = CASE WHEN $end_date IS NULL THEN NULL ELSE toString($end_date) END
                WITH p
                MATCH (b:BankEntity {bank_id: $bank_id})
                MERGE (b)-[:HAS_PROJECT]->(p)
            """,
            project_id=p.project_id,
            name=p.name,
            description=p.description,
            status=str(p.status),
            budget=p.budget_usd,
            start_date=p.start_date,
            end_date=p.end_date,
            bank_id=p.bank_id)

            neo.run("""
                MERGE (s:ProjectStatus {name: $status})
                WITH s
                MATCH (p:ProjectEntity {project_id: $project_id})
                MERGE (p)-[:HAS_STATUS]->(s)
            """,
            status=str(p.status),
            project_id=p.project_id)

            for stakeholder_id in p.stakeholder_ids:
                neo.run("""
                    MATCH (p:ProjectEntity {project_id: $project_id})
                    MATCH (per:PersonnelEntity {personnel_id: $personnel_id})
                    MERGE (p)-[:HAS_STAKEHOLDER]->(per)
                """,
                project_id=p.project_id,
                personnel_id=stakeholder_id)

        # PERSONNEL
        for person in get_all_personnel(session):
            neo.run("""
                MERGE (per:PersonnelEntity {personnel_id: $personnel_id})
                SET per.full_name = $full_name,
                    per.department = $department,
                    per.email = $email,
                    per.years_experience = $years_experience
                WITH per
                MATCH (b:BankEntity {bank_id: $bank_id})
                MERGE (per)-[:BELONGS_TO]->(b)
            """,
            personnel_id=person.personnel_id,
            full_name=person.full_name,
            department=person.department,
            email=person.email,
            years_experience=person.years_experience,
            bank_id=person.bank_id)

            neo.run("""
                MERGE (r:PersonnelRole {name: $role})
                WITH r
                MATCH (per:PersonnelEntity {personnel_id: $personnel_id})
                MERGE (per)-[:HAS_ROLE]->(r)
            """,
            role=str(person.role),
            personnel_id=person.personnel_id)

        # REGULATIONS
        for reg in get_all_regulations(session):
            neo.run("""
                MERGE (r:RegulationEntity {regulation_id: $regulation_id})
                SET r.code = $code,
                    r.title = $title,
                    r.issuing_body = $issuing_body,
                    r.effective_date = toString($effective_date),
                    r.summary = $summary
            """,
            regulation_id=reg.regulation_id,
            code=reg.code,
            title=reg.title,
            issuing_body=reg.issuing_body,
            effective_date=reg.effective_date,
            summary=reg.summary)

            for bank_id in reg.applicable_bank_ids:
                neo.run("""
                    MATCH (r:RegulationEntity {regulation_id: $regulation_id})
                    MATCH (b:BankEntity {bank_id: $bank_id})
                    MERGE (r)-[:APPLIES_TO]->(b)
                """,
                regulation_id=reg.regulation_id,
                bank_id=bank_id)

        # BANK PROFILE
        for bank in get_all_banks(session):
            profile = get_bank_profile(session, bank.bank_id)
            if not profile:
                continue

            neo.run("""
                MERGE (bp:BankProfile {bank_id: $bank_id})
                SET bp.mission = $mission,
                    bp.vision = $vision,
                    bp.architecture_style = $architecture_style,
                    bp.core_banking_system = $core_banking_system,
                    bp.data_platform = $data_platform,
                    bp.org_structure_notes = $org_structure_notes,
                    bp.additional_context = $additional_context
            """,
            bank_id=profile.bank_id,
            mission=profile.mission,
            vision=profile.vision,
            architecture_style=profile.architecture_style,
            core_banking_system=profile.core_banking_system,
            data_platform=profile.data_platform,
            org_structure_notes=profile.org_structure_notes,
            additional_context=profile.additional_context)

            neo.run("""
                MATCH (b:BankEntity {bank_id: $bank_id})
                MATCH (bp:BankProfile {bank_id: $bank_id})
                MERGE (b)-[:HAS_PROFILE]->(bp)
            """, bank_id=profile.bank_id)

            def merge_list(label, rel, values):
                for value in values:
                    neo.run(f"""
                        MERGE (n:{label} {{name: $value}})
                        WITH n
                        MATCH (bp:BankProfile {{bank_id: $bank_id}})
                        MERGE (bp)-[:{rel}]->(n)
                    """, value=value, bank_id=profile.bank_id)

            merge_list("CoreProcess", "HAS_CORE_PROCESS", profile.core_processes)
            merge_list("SupportProcess", "HAS_SUPPORT_PROCESS", profile.support_processes)
            merge_list("ProgrammingLanguage", "USES_LANGUAGE", profile.programming_languages)
            merge_list("DatabaseTechnology", "USES_DATABASE", profile.databases)
            merge_list("CloudProvider", "USES_CLOUD", profile.cloud_providers)
            merge_list("DevOpsTool", "USES_DEVOPS", profile.devops_tools)
            merge_list("IntegrationMiddleware", "USES_MIDDLEWARE", profile.integration_middleware)
            merge_list("SecurityTool", "USES_SECURITY_TOOL", profile.security_stack)
            merge_list("ArchitectureLayer", "HAS_ARCHITECTURE_LAYER", profile.architecture_layers)
            merge_list("KeySystem", "HAS_KEY_SYSTEM", profile.key_systems)
            merge_list("ExternalIntegration", "HAS_EXTERNAL_INTEGRATION", profile.external_integrations)
            merge_list("AnalyticsTool", "HAS_ANALYTICS_TOOL", profile.analytics_tools)
            merge_list("AIMLCapability", "HAS_AI_ML_CAPABILITY", profile.ai_ml_capabilities)
            merge_list("DigitalChannel", "HAS_DIGITAL_CHANNEL", profile.digital_channels)
            merge_list("PhysicalChannel", "HAS_PHYSICAL_CHANNEL", profile.physical_channels)
            merge_list("PartnerChannel", "HAS_PARTNER_CHANNEL", profile.partner_channels)
            merge_list("Department", "HAS_DEPARTMENT", profile.key_departments)

            for objective in profile.strategic_objectives:
                neo.run("""
                    MERGE (o:StrategicObjective {name: $value})
                    WITH o
                    MATCH (bp:BankProfile {bank_id: $bank_id})
                    MERGE (bp)-[:HAS_STRATEGIC_OBJECTIVE]->(o)
                """, value=objective, bank_id=profile.bank_id)

            for adv in profile.competitive_advantages:
                neo.run("""
                    MERGE (a:CompetitiveAdvantage {name: $value})
                    WITH a
                    MATCH (bp:BankProfile {bank_id: $bank_id})
                    MERGE (bp)-[:HAS_COMPETITIVE_ADVANTAGE]->(a)
                """, value=adv, bank_id=profile.bank_id)

            for ev in profile.evolution_history:
                neo.run("""
                    CREATE (e:EvolutionEvent {
                        bank_id: $bank_id,
                        event_date: toString($event_date),
                        category: $category,
                        title: $title,
                        description: $description
                    })
                """,
                bank_id=profile.bank_id,
                event_date=ev.event_date,
                category=ev.category,
                title=ev.title,
                description=ev.description)

                neo.run("""
                    MATCH (bp:BankProfile {bank_id: $bank_id})
                    MATCH (e:EvolutionEvent {bank_id: $bank_id, title: $title, event_date: toString($event_date)})
                    MERGE (bp)-[:HAS_EVOLUTION_EVENT]->(e)
                """,
                bank_id=profile.bank_id,
                title=ev.title,
                event_date=ev.event_date)

    driver.close()
    session.close()
    print("✅ Master KG construido correctamente")


if __name__ == "__main__":
    build_master_kg()