from app.services.sauth_capture import capture_from_text


def test_capture_from_json_text():
    text = (
        'prefix {"client_login_sn":"sn-1","udid":"u-1","deviceid":"d-1",'
        '"sdkuid":"sdk-1","sessionid":"session-1"} suffix'
    )
    result = capture_from_text(text)

    assert result is not None
    assert result["client_login_sn"] == "sn-1"
    assert result["sessionid"] == "session-1"


def test_capture_from_launcher_wrapper():
    text = (
        '{"sauth_json":{"client_login_sn":"sn-2","udid":"u-2",'
        '"device_id":"d-2","sdkuid":"sdk-2","session_id":"session-2"}}'
    )
    result = capture_from_text(text)

    assert result is not None
    assert result["deviceid"] == "d-2"
    assert result["sessionid"] == "session-2"
