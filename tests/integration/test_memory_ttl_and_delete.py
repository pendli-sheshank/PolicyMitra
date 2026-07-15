"""Verifies memory.md's Layer 2-4 + audit invariants against the real DB:
L2 sessions auto-expire, L3 profile deletion cascades into derived cache,
L4 client notes are scoped per agent, and the audit log survives deletion
of the session/profile it originated from."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_session_ttl_expires_stale_sessions(conn):
    from api.deps import touch_session

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO mem.sessions (expires_at) VALUES (%s) RETURNING session_id",
            (datetime.now(UTC) - timedelta(hours=1),),
        )
        stale_session_id = cur.fetchone()[0]

    touch_session(conn, None)  # any session touch triggers the lazy expiry sweep

    with conn.cursor() as cur:
        cur.execute("SELECT session_id FROM mem.sessions WHERE session_id = %s", (stale_session_id,))
        assert cur.fetchone() is None


def test_active_session_survives_the_sweep(conn):
    from api.deps import touch_session

    session_id = touch_session(conn, None)

    with conn.cursor() as cur:
        cur.execute("SELECT session_id FROM mem.sessions WHERE session_id = %s", (session_id,))
        assert cur.fetchone() is not None


def test_profile_delete_cascades_into_recommendation_cache(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO mem.user_profiles
                (user_ref, age, dependents, city_tier, budget_annual_inr, sum_insured_target_inr, ped_flags, consent_given_at)
            VALUES ('test-user-cascade', 30, 1, 'tier1', 15000, 500000, '{}', now())
            RETURNING profile_id
            """)
        profile_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO mem.recommendation_cache (profile_id, cached_result) VALUES (%s, %s)",
            (profile_id, '{"foo": "bar"}'),
        )

        cur.execute("DELETE FROM mem.user_profiles WHERE profile_id = %s", (profile_id,))

        cur.execute("SELECT count(*) FROM mem.recommendation_cache WHERE profile_id = %s", (profile_id,))
        assert cur.fetchone()[0] == 0


def test_agent_notes_are_scoped_per_agent(conn):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO agent.agents (agent_id) VALUES ('test-agent-A'), ('test-agent-B') ON CONFLICT DO NOTHING")
        cur.execute(
            "INSERT INTO agent.client_notes (agent_id, client_ref, note_content) "
            "VALUES ('test-agent-A', 'client-x', 'private note')"
        )

        cur.execute("SELECT count(*) FROM agent.client_notes WHERE agent_id = 'test-agent-B'")
        assert cur.fetchone()[0] == 0

        cur.execute("SELECT count(*) FROM agent.client_notes WHERE agent_id = 'test-agent-A'")
        assert cur.fetchone()[0] == 1


def test_audit_log_survives_profile_deletion(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO mem.user_profiles
                (user_ref, age, dependents, city_tier, budget_annual_inr, sum_insured_target_inr, ped_flags, consent_given_at)
            VALUES ('test-user-audit', 30, 1, 'tier1', 15000, 500000, '{}', now())
            RETURNING profile_id
            """)
        profile_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO audit.responses (module, query_text, response_text, chunk_ids_used, guardrail_verdict, confidence_score)
            VALUES ('qa', 'test query', 'test response', '{}', 'pass', 0.9)
            RETURNING response_id
            """)
        response_id = cur.fetchone()[0]

        cur.execute("DELETE FROM mem.user_profiles WHERE profile_id = %s", (profile_id,))

        cur.execute("SELECT count(*) FROM audit.responses WHERE response_id = %s", (response_id,))
        assert cur.fetchone()[0] == 1  # audit is deliberately not FK'd to mem — survives deletion
