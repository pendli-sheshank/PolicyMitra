-- Layer 3: User Profile Memory. Cross-session, OPT-IN ONLY.
-- consent_given_at is NOT NULL to structurally enforce that nothing here is
-- ever written implicitly from a session (memory.md).

CREATE TABLE IF NOT EXISTS mem_user_profiles (
    profile_id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                                substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                                substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    user_ref                TEXT NOT NULL UNIQUE,
    age                     INTEGER,
    dependents              INTEGER,
    city_tier               TEXT CHECK (city_tier IN ('tier1', 'tier2', 'tier3')),
    budget_annual_inr       INTEGER,
    sum_insured_target_inr  INTEGER,
    ped_flags               TEXT NOT NULL DEFAULT '{}',
    consent_given_at        TEXT NOT NULL,
    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')),
    updated_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);

-- Derived cache keyed off a profile. ON DELETE CASCADE makes deletion-on-request
-- (memory.md §5) structurally cascade through this derived index automatically.
-- (Requires PRAGMA foreign_keys=ON — set on every connection in db/connection.py.)
CREATE TABLE IF NOT EXISTS mem_recommendation_cache (
    cache_id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                        substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                        substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    profile_id      TEXT NOT NULL REFERENCES mem_user_profiles(profile_id) ON DELETE CASCADE,
    cached_result   TEXT NOT NULL,
    computed_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);

CREATE INDEX IF NOT EXISTS idx_mem_reco_cache_profile ON mem_recommendation_cache (profile_id);
