from pathlib import Path

from hydromt_fiat.data.utils import file_hash


def test_file_hash(tmp_json: Path):
    # Call the function
    h = file_hash(tmp_json)
    # Assert the output, sha256
    assert h == "9a57ab963760444eb00dacd0294013a3dbe13aec7a67683051eafa76f93a7bd4"


def test_file_hash_md5(tmp_json: Path):
    # Call the function
    h = file_hash(tmp_json, hash_alg="md5")
    # Assert the output, md5
    assert h == "bc658802f807c48febd52131864f1287"
