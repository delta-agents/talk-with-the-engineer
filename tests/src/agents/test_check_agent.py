from talk_with_the_engineer.agents import RulesOfThumb


def test_rules_of_thumb_agent_imports_and_instantiates():
    agent = RulesOfThumb(db_path="")
    assert agent is not None
