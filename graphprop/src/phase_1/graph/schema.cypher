// =========================================================
// Constraints
// =========================================================

CREATE CONSTRAINT bank_id_unique IF NOT EXISTS
FOR (b:BankEntity)
REQUIRE b.bank_id IS UNIQUE;

CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:ProjectEntity)
REQUIRE p.project_id IS UNIQUE;

CREATE CONSTRAINT personnel_id_unique IF NOT EXISTS
FOR (p:PersonnelEntity)
REQUIRE p.personnel_id IS UNIQUE;

CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS
FOR (r:RegulationEntity)
REQUIRE r.regulation_id IS UNIQUE;

CREATE CONSTRAINT source_document_file_hash_unique IF NOT EXISTS
FOR (d:SourceDocument)
REQUIRE d.file_hash IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk)
REQUIRE c.chunk_id IS UNIQUE;

CREATE CONSTRAINT chunk_hash_unique IF NOT EXISTS
FOR (c:Chunk)
REQUIRE c.chunk_hash IS UNIQUE;

CREATE CONSTRAINT page_id_unique IF NOT EXISTS
FOR (p:Page)
REQUIRE p.page_id IS UNIQUE;

CREATE CONSTRAINT multimodal_chunk_id_unique IF NOT EXISTS
FOR (mm:MultiModalChunk)
REQUIRE mm.chunk_id IS UNIQUE;

CREATE CONSTRAINT multimodal_chunk_hash_unique IF NOT EXISTS
FOR (mm:MultiModalChunk)
REQUIRE mm.chunk_hash IS UNIQUE;

CREATE CONSTRAINT workspace_id_unique IF NOT EXISTS
FOR (w:Workspace)
REQUIRE w.workspace_id IS UNIQUE;


// =========================================================
// Optional indexes
// =========================================================

CREATE INDEX source_document_name_idx IF NOT EXISTS
FOR (d:SourceDocument)
ON (d.name);

CREATE INDEX source_document_type_idx IF NOT EXISTS
FOR (d:SourceDocument)
ON (d.document_type);

CREATE INDEX source_document_arch_state_idx IF NOT EXISTS
FOR (d:SourceDocument)
ON (d.architecture_state);

CREATE INDEX chunk_document_type_idx IF NOT EXISTS
FOR (c:Chunk)
ON (c.document_type);

CREATE INDEX chunk_arch_state_idx IF NOT EXISTS
FOR (c:Chunk)
ON (c.architecture_state);

CREATE INDEX multimodal_chunk_document_type_idx IF NOT EXISTS
FOR (mm:MultiModalChunk)
ON (mm.document_type);

CREATE INDEX multimodal_chunk_arch_state_idx IF NOT EXISTS
FOR (mm:MultiModalChunk)
ON (mm.architecture_state);

CREATE INDEX page_number_idx IF NOT EXISTS
FOR (p:Page)
ON (p.page_number);