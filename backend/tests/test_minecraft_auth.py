from app.utils.mc_auth_toolkit import PeAuthCodec, UserTokenCodec


def test_pe_codec_roundtrip():
    packet = PeAuthCodec.decrypt(PeAuthCodec.encrypt({"hello": "world"}))
    assert packet.plain_json == {"hello": "world"}


def test_user_token_length():
    token = UserTokenCodec.generate("token", "/user-allfriends", "{}")
    assert len(token) == 17
