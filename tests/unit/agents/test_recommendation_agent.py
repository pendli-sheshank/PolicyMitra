from agents.recommendation_agent import PlanFactSheet, Profile, RecommendationAgent, _score_plan


def _profile(**overrides) -> Profile:
    base = dict(
        age=34,
        dependents=2,
        city_tier="tier2",
        ped_flags={"Diabetes Mellitus": True},
        budget_annual_inr=15000,
        sum_insured_target_inr=500000,
    )
    base.update(overrides)
    return Profile(**base)


def test_shorter_ped_wait_scores_higher_when_budget_equal():
    profile = _profile()
    short_wait = PlanFactSheet(
        insurer="A",
        premium_inr=15000,
        ped_waiting_periods_months={"Diabetes Mellitus": 12},
        sum_insured_options_inr=[500000],
    )
    long_wait = PlanFactSheet(
        insurer="B",
        premium_inr=15000,
        ped_waiting_periods_months={"Diabetes Mellitus": 36},
        sum_insured_options_inr=[500000],
    )

    assert _score_plan(profile, short_wait) > _score_plan(profile, long_wait)


def test_over_budget_plan_scores_lower_than_within_budget_plan():
    profile = _profile()
    within_budget = PlanFactSheet(
        insurer="A",
        premium_inr=12000,
        ped_waiting_periods_months={"Diabetes Mellitus": 24},
        sum_insured_options_inr=[500000],
    )
    over_budget = PlanFactSheet(
        insurer="B",
        premium_inr=30000,
        ped_waiting_periods_months={"Diabetes Mellitus": 24},
        sum_insured_options_inr=[500000],
    )

    assert _score_plan(profile, within_budget) > _score_plan(profile, over_budget)


def test_recommend_ranks_by_score_and_fills_trade_off_for_non_top_picks():
    profile = _profile()
    better = PlanFactSheet(
        insurer="A",
        premium_inr=15000,
        premium_clause_id="CL-PREMIUM-TABLE#5_00_000",
        ped_waiting_periods_months={"Diabetes Mellitus": 12},
        sum_insured_options_inr=[500000],
    )
    worse = PlanFactSheet(
        insurer="B",
        premium_inr=15000,
        premium_clause_id="CL-PREMIUM-TABLE#5_00_000",
        ped_waiting_periods_months={"Diabetes Mellitus": 36},
        sum_insured_options_inr=[500000],
    )

    agent = RecommendationAgent(llm_client=None)
    ranked = agent.recommend(profile, [worse, better])

    assert ranked[0].insurer == "A"
    assert ranked[0].rank == 1
    assert ranked[0].trade_off_vs_top_pick is None
    assert ranked[1].trade_off_vs_top_pick is not None


def test_advise_portability_full_credit_when_already_served_enough():
    agent = RecommendationAgent(llm_client=None)
    advice = agent.advise_portability(months_on_current_plan=24, candidate_waiting_period_months=12)

    assert advice.credited_months == 12
    assert advice.remaining_wait_months == 0
    assert advice.recommendation == "port"


def test_advise_portability_partial_credit():
    agent = RecommendationAgent(llm_client=None)
    advice = agent.advise_portability(months_on_current_plan=6, candidate_waiting_period_months=24)

    assert advice.credited_months == 6
    assert advice.remaining_wait_months == 18
    assert advice.recommendation == "stay_or_wait"
