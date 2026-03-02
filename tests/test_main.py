from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database.database import Base
from database.models import User, Post


class DummyRequest:
    def __init__(self):
        self.session = {}


class DummyTemplates:
    def __init__(self):
        self.calls = []

    def TemplateResponse(self, template_name, context):
        self.calls.append((template_name, context))
        return {"template": template_name, "context": context}


class BrokenRegisterSession:
    def add(self, _):
        raise Exception("db add error")

    def commit(self):
        pass

    def refresh(self, _):
        pass

    def close(self):
        pass


class BrokenLoginSession:
    class _Query:
        def filter(self, *_args, **_kwargs):
            raise Exception("db query error")

    def query(self, *_args, **_kwargs):
        return self._Query()

    def close(self):
        pass


class BrokenSavePostSession:
    def add(self, _):
        raise Exception("db add error")

    def commit(self):
        pass

    def refresh(self, _):
        pass

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def setup_test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(main, "SessionLocal", testing_session_local)


def test_home_renders_index(monkeypatch):
    dummy_templates = DummyTemplates()
    monkeypatch.setattr(main, "templates", dummy_templates)

    req = DummyRequest()
    response = main.home(req)

    assert response["template"] == "index.html"
    assert response["context"]["request"] is req


def test_test_endpoint():
    assert main.test() == {"status": "OK"}


def test_register_get_renders_template(monkeypatch):
    dummy_templates = DummyTemplates()
    monkeypatch.setattr(main, "templates", dummy_templates)

    register_get_endpoint = next(
        route.endpoint
        for route in main.app.routes
        if getattr(route, "path", None) == "/register" and "GET" in getattr(route, "methods", set())
    )

    req = DummyRequest()
    response = register_get_endpoint(req)

    assert response["template"] == "register.html"


def test_register_post_success(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)

    response = main.test_register("alice", "secret")
    assert response.status_code == 302
    assert response.headers["location"] == "/post"

    db = main.SessionLocal()
    try:
        user = db.query(User).filter(User.username == "alice").first()
        assert user is not None
        assert user.password == "secret"
    finally:
        db.close()


def test_register_post_exception(monkeypatch):
    monkeypatch.setattr(main, "SessionLocal", lambda: BrokenRegisterSession())

    response = main.test_register("u", "p")
    assert response is None


def test_login_get_renders_template(monkeypatch):
    dummy_templates = DummyTemplates()
    monkeypatch.setattr(main, "templates", dummy_templates)

    req = DummyRequest()
    response = main.register(req)

    assert response["template"] == "login.html"


def test_login_wrong_password(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    dummy_templates = DummyTemplates()
    monkeypatch.setattr(main, "templates", dummy_templates)

    db = main.SessionLocal()
    try:
        db.add(User(username="bob", password="good"))
        db.commit()
    finally:
        db.close()

    req = DummyRequest()
    response = main.login(req, "bob", "bad")

    assert response["template"] == "login.html"
    assert "Incorrect username or password" in response["context"]["error_message"]


def test_login_success_sets_session_and_redirects(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)

    db = main.SessionLocal()
    try:
        db.add(User(username="charlie", password="pw"))
        db.commit()
        user = db.query(User).filter(User.username == "charlie").first()
    finally:
        db.close()

    req = DummyRequest()
    response = main.login(req, "charlie", "pw")

    assert response.status_code == 302
    assert response.headers["location"] == "/post"
    assert req.session["user_id"] == user.id
    assert req.session["username"] == "charlie"


def test_login_exception(monkeypatch):
    monkeypatch.setattr(main, "SessionLocal", lambda: BrokenLoginSession())

    req = DummyRequest()
    response = main.login(req, "x", "y")
    assert response is None


def test_protected_redirects_without_session():
    req = DummyRequest()
    response = main.protected(req)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_protected_allows_with_session():
    req = DummyRequest()
    req.session["user_id"] = 123

    assert main.protected(req) == {"ok": True}


def test_post_page_requires_login():
    req = DummyRequest()
    response = main.post_page(req)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_post_page_renders_for_logged_user(monkeypatch):
    dummy_templates = DummyTemplates()
    monkeypatch.setattr(main, "templates", dummy_templates)

    req = DummyRequest()
    req.session["user_id"] = 1

    response = main.post_page(req)
    assert response["template"] == "blog.html"


def test_save_post_requires_login():
    req = DummyRequest()
    response = main.save_post(req, "t", "c")

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_save_post_success(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)

    db = main.SessionLocal()
    try:
        user = User(username="writer", password="pw")
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    req = DummyRequest()
    req.session["user_id"] = user_id

    response = main.save_post(req, "My post", "Body")
    assert response.status_code == 302
    assert response.headers["location"] == "/post"

    db = main.SessionLocal()
    try:
        post = db.query(Post).filter(Post.title == "My post").first()
        assert post is not None
        assert post.content == "Body"
        assert post.user_id == user_id
    finally:
        db.close()


def test_save_post_exception_rolls_back(monkeypatch):
    broken = BrokenSavePostSession()
    monkeypatch.setattr(main, "SessionLocal", lambda: broken)

    req = DummyRequest()
    req.session["user_id"] = 1

    response = main.save_post(req, "bad", "bad")
    assert response.status_code == 302
    assert response.headers["location"] == "/post"
    assert getattr(broken, "rolled_back", False)
