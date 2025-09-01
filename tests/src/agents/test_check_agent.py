from skip_the_engineer.agents import AIAgent1, AIAgent2


def test_check_config_agent_import():
    """Basic check to see if agents import"""
    agent = AIAgent1(db_path="")
    assert agent is not None, (
        "AIagent1 should be imported and instantiated successfully."
    )


def test_check_webservice_agent_import():
    """Basic check to see if agents import"""
    agent = AIAgent2(db_path="")
    assert agent is not None, (
        "AIagent2 should be imported and instantiated successfully."
    )
