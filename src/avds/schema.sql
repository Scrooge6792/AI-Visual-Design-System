PRAGMA journal_mode=DELETE;
PRAGMA synchronous=FULL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files(
  file_hash TEXT PRIMARY KEY, relative_path TEXT NOT NULL UNIQUE, format TEXT NOT NULL,
  mime_type TEXT NOT NULL, byte_size INTEGER NOT NULL, width INTEGER NOT NULL,
  height INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS import_batches(
  batch_id TEXT PRIMARY KEY, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets(
  asset_id TEXT PRIMARY KEY, file_hash TEXT NOT NULL REFERENCES files(file_hash),
  state TEXT NOT NULL CHECK(state IN ('staged','active','archived')),
  revision INTEGER NOT NULL, title TEXT, description TEXT, design_value TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_sources(
  source_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id),
  original_name TEXT NOT NULL, origin TEXT, source_url TEXT, author TEXT,
  copyright TEXT, license TEXT, user_note TEXT, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_relations(
  source_asset_id TEXT NOT NULL REFERENCES assets(asset_id),
  relation_type TEXT NOT NULL CHECK(relation_type IN ('similar','derived','series')),
  target_asset_id TEXT NOT NULL REFERENCES assets(asset_id),
  PRIMARY KEY(source_asset_id,relation_type,target_asset_id), CHECK(source_asset_id <> target_asset_id)
);
CREATE TABLE IF NOT EXISTS review_queue_items(
  queue_item_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES import_batches(batch_id),
  asset_id TEXT NOT NULL REFERENCES assets(asset_id), position INTEGER NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('pending','in_review','deferred','resolved')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(batch_id, position)
);
CREATE TABLE IF NOT EXISTS analysis_runs(
  analysis_run_id TEXT PRIMARY KEY, queue_item_id TEXT REFERENCES review_queue_items(queue_item_id),
  asset_id TEXT REFERENCES assets(asset_id), model TEXT NOT NULL, prompt_version TEXT NOT NULL,
  execution_location TEXT NOT NULL, body_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS change_proposals(
  proposal_id TEXT NOT NULL, revision INTEGER NOT NULL, operation TEXT NOT NULL,
  operation_id TEXT NOT NULL, target_kind TEXT NOT NULL, target_id TEXT NOT NULL,
  target_revision INTEGER NOT NULL, file_hash TEXT, body_json TEXT NOT NULL,
  proposal_hash TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('draft','in_review','approved','rejected','superseded')),
  created_at TEXT NOT NULL, PRIMARY KEY(proposal_id, revision)
);
CREATE TABLE IF NOT EXISTS concepts(
  concept_id TEXT PRIMARY KEY, preferred_name TEXT NOT NULL, facet TEXT NOT NULL,
  definition TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS concept_terms(
  term_id TEXT PRIMARY KEY, concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
  language TEXT NOT NULL, term TEXT NOT NULL, normalized_term TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('preferred','alias')), UNIQUE(normalized_term, language)
);
CREATE TABLE IF NOT EXISTS concept_relations(
  source_concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
  kind TEXT NOT NULL CHECK(kind IN ('broader','narrower','related')),
  target_concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
  PRIMARY KEY(source_concept_id, kind, target_concept_id), CHECK(source_concept_id <> target_concept_id)
);
CREATE TABLE IF NOT EXISTS concept_revisions(
  concept_id TEXT NOT NULL REFERENCES concepts(concept_id), revision INTEGER NOT NULL,
  body_json TEXT NOT NULL, proposal_id TEXT NOT NULL, review_event_id TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY(concept_id, revision)
);
CREATE TABLE IF NOT EXISTS concept_candidates(
  candidate_id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL, state TEXT NOT NULL,
  resolved_concept_id TEXT REFERENCES concepts(concept_id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_concepts(
  asset_id TEXT NOT NULL REFERENCES assets(asset_id), concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
  judgment_kind TEXT NOT NULL DEFAULT 'B', PRIMARY KEY(asset_id, concept_id)
);
CREATE TABLE IF NOT EXISTS review_events(
  review_event_id TEXT PRIMARY KEY, action TEXT NOT NULL, proposal_id TEXT,
  proposal_revision INTEGER, proposal_hash TEXT, file_hash TEXT, target_revision INTEGER,
  reviewer_path TEXT NOT NULL, created_at TEXT NOT NULL, detail_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations(
  operation_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, state TEXT NOT NULL,
  result_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_documents(
  asset_id TEXT PRIMARY KEY REFERENCES assets(asset_id), title TEXT NOT NULL,
  description TEXT NOT NULL, design_value TEXT NOT NULL, terms TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_articles(
  knowledge_id TEXT PRIMARY KEY, state TEXT NOT NULL CHECK(state IN ('active','archived')),
  revision INTEGER NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL,
  relative_path TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_revisions(
  knowledge_id TEXT NOT NULL REFERENCES knowledge_articles(knowledge_id), revision INTEGER NOT NULL,
  title TEXT NOT NULL, summary TEXT NOT NULL, relative_path TEXT NOT NULL,
  proposal_id TEXT NOT NULL, review_event_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(knowledge_id,revision)
);
CREATE TABLE IF NOT EXISTS knowledge_links(
  knowledge_id TEXT NOT NULL REFERENCES knowledge_articles(knowledge_id), target_kind TEXT NOT NULL,
  target_id TEXT NOT NULL, PRIMARY KEY(knowledge_id,target_kind,target_id)
);
CREATE TABLE IF NOT EXISTS prompt_modules(
  prompt_id TEXT PRIMARY KEY, state TEXT NOT NULL CHECK(state IN ('active','archived')),
  revision INTEGER NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL,
  relative_path TEXT NOT NULL, body_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_revisions(
  prompt_id TEXT NOT NULL REFERENCES prompt_modules(prompt_id), revision INTEGER NOT NULL,
  name TEXT NOT NULL, relative_path TEXT NOT NULL, body_json TEXT NOT NULL,
  proposal_id TEXT NOT NULL, review_event_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(prompt_id,revision)
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(knowledge_id UNINDEXED,title,summary,body,tokenize='unicode61');
CREATE TABLE IF NOT EXISTS visual_features(
  asset_id TEXT PRIMARY KEY REFERENCES assets(asset_id), file_hash TEXT NOT NULL,
  relative_path TEXT NOT NULL, engine_version TEXT NOT NULL, os_build TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
  asset_id UNINDEXED, title, description, design_value, terms, tokenize='unicode61'
);
CREATE INDEX IF NOT EXISTS idx_queue_batch_state ON review_queue_items(batch_id, state);
CREATE INDEX IF NOT EXISTS idx_proposal_state ON change_proposals(state, created_at);
CREATE INDEX IF NOT EXISTS idx_asset_state ON assets(state, updated_at);
