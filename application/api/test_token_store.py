import json
from pathlib import Path

from application.api.token_store import TokenData, TokenStore


class TestTokenData:
    def test_default_values(self):
        td = TokenData()
        assert td.access == ""
        assert td.refresh == ""
        assert td.username == ""

    def test_is_authenticated_with_token(self):
        td = TokenData(access="acc1")
        assert td.is_authenticated is True

    def test_is_authenticated_without_token(self):
        td = TokenData(access="")
        assert td.is_authenticated is False

    def test_is_authenticated_with_whitespace(self):
        td = TokenData(access="  ")
        assert td.is_authenticated is True


class TestTokenStoreInit:
    def test_default_path(self):
        store = TokenStore()
        assert store.path == Path.home() / ".mymoney" / "tokens.json"

    def test_custom_path(self, tmp_path):
        store = TokenStore(tmp_path / "custom.json")
        assert store.path == tmp_path / "custom.json"

    def test_custom_path_string(self, tmp_path):
        path = str(tmp_path / "tokens.json")
        store = TokenStore(path)
        assert store.path == Path(path)


class TestTokenStoreLoad:
    def test_load_empty(self, tmp_path):
        store = TokenStore(tmp_path / "tokens.json")
        data = store.load()
        assert data.access == ""
        assert data.refresh == ""
        assert data.username == ""

    def test_load_existing(self, tmp_path):
        path = tmp_path / "tokens.json"
        path.write_text(json.dumps({"access": "a", "refresh": "r", "username": "u"}), encoding="utf-8")
        store = TokenStore(path)
        data = store.load()
        assert data.access == "a"
        assert data.refresh == "r"
        assert data.username == "u"

    def test_load_corrupted_json(self, tmp_path):
        path = tmp_path / "tokens.json"
        path.write_text("not json {{{", encoding="utf-8")
        store = TokenStore(path)
        data = store.load()
        assert data.access == ""

    def test_load_partial_json(self, tmp_path):
        path = tmp_path / "tokens.json"
        path.write_text(json.dumps({"access": "token123"}), encoding="utf-8")
        store = TokenStore(path)
        data = store.load()
        assert data.access == "token123"
        assert data.refresh == ""


class TestTokenStoreSave:
    def test_save_creates_file(self, tmp_path):
        path = tmp_path / "tokens.json"
        store = TokenStore(path)
        store.save(TokenData(access="a", refresh="r", username="u"))
        assert path.exists()

    def test_save_persists_data(self, tmp_path):
        path = tmp_path / "tokens.json"
        store = TokenStore(path)
        store.save(TokenData(access="acc1", refresh="ref1", username="alice"))
        loaded = store.load()
        assert loaded.access == "acc1"
        assert loaded.refresh == "ref1"
        assert loaded.username == "alice"

    def test_save_overwrites(self, tmp_path):
        path = tmp_path / "tokens.json"
        store = TokenStore(path)
        store.save(TokenData(access="first", refresh="r", username="u"))
        store.save(TokenData(access="second", refresh="r", username="u"))
        loaded = store.load()
        assert loaded.access == "second"

    def test_save_creates_parent_dir(self, tmp_path):
        path = tmp_path / "subdir" / "tokens.json"
        store = TokenStore(path)
        store.save(TokenData(access="a"))
        assert path.exists()

    def test_save_atomic(self, tmp_path):
        path = tmp_path / "tokens.json"
        store = TokenStore(path)
        store.save(TokenData(access="acc1", refresh="ref1", username="u"))
        assert path.exists()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestTokenStoreClear:
    def test_clear_removes_file(self, tmp_path):
        path = tmp_path / "tokens.json"
        store = TokenStore(path)
        store.save(TokenData(access="a"))
        assert path.exists()
        store.clear()
        assert not path.exists()

    def test_clear_nonexistent_file(self, tmp_path):
        path = tmp_path / "tokens.json"
        store = TokenStore(path)
        store.clear()
        assert not path.exists()
