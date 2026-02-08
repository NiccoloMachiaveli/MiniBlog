import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.database import engine, Base, SessionLocal
from database.models import User
from database import models
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-me-secret-key")

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test")
def test():
    return {"status": "OK"}


@app.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def test_register(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        new_user = User(username=username, password=password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return RedirectResponse(url="/post", status_code=302)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


@app.get("/login", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or user.password != password:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error_message": "Incorrect username or password"},
            )
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        return RedirectResponse(url="/post", status_code=302)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


@app.get("/protected")
def protected(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    return {"ok": True}


@app.get("/post", response_class=HTMLResponse)
def post_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("blog.html", {"request": request})


@app.post("/post")
def save_post(request: Request, username: str = Form(...), title: str = Form(...), content: str = Form(...)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    db = SessionLocal()
    try:
        pass
    except:
        pass
    finally:
        pass
    return


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
