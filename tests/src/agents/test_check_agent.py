from talk_with_the_engineer.agents import Prerequisites, RulesOfThumb


def test_check_config_agent_import():
    """Basic check to see if agents import"""
    agent = RulesOfThumb(db_path="")
    assert agent is not None, (
        "AIagent1 should be imported and instantiated successfully."
    )


def test_check_webservice_agent_import():
    """Basic check to see if agents import"""
    agent = Prerequisites(db_path="")
    assert agent is not None, (
        "AIagent2 should be imported and instantiated successfully."
    )
