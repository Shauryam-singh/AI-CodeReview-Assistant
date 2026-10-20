from app.services.existing.risk_service import infer_risk


def test_sql_injection_risk():
    assert infer_risk("SQL Injection detected in query") == (
        "Attackers can read or modify database data."
    )


def test_eval_and_exec_map_to_rce():
    expected = "Remote code execution vulnerability."
    assert infer_risk("Dangerous function 'eval' detected.") == expected
    assert infer_risk("Dangerous function 'exec' detected.") == expected


def test_case_insensitive_matching():
    assert infer_risk("SQL INJECTION FOUND") == (
        "Attackers can read or modify database data."
    )


def test_unknown_message_gets_default_risk():
    assert infer_risk("Something odd happened") == (
        "Potential security or reliability issue."
    )
