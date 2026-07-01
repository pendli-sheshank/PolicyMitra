-- Layer 3: User Profile Memory. Cross-session, OPT-IN ONLY.
-- consent_given_at is NOT NULL to structurally enforce that nothing here is
-- ever written implicitly from a session (memory.md).

CREATE TABLE IF NOT EXISTS mem.user_profiles (
    profile_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_ref                TEXT NOT NULL UNIQUE,
    age                     INTEGER,
    dependents              INTEGER,
    city_tier               TEXT CHECK (city_tier IN ('tier1', 'tier2', 'tier3')),
    budget_annual_inr       INTEGER,
    sum_insured_target_inr  INTEGER,
    ped_flags               JSONB NOT NULL DEFAULT '{}'::jsonb,
    consent_given_at        TIMESTAMPTZ NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Derived cache keyed off a profile. ON DELETE CASCADE makes deletion-on-request
-- (memory.md §5) structurally cascade through this derived index automatically.
CREATE TABLE IF NOT EXISTS mem.recommendation_cache (
    cache_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES mem.user_profiles(profile_id) ON DELETE CASCADE,
    cached_result   JSONB NOT NULL,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mem_reco_cache_profile ON mem.recommendation_cache (profile_id);
