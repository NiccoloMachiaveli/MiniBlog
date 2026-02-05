import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.database import engine, Base, SessionLocal
from database.models import User
from database import models
from fastapi.responses import RedirectResponse

app = FastAPI()

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
def login():
    pass


@app.get("/protected")
def protected():
    pass


@app.get("/post", response_class=HTMLResponse)
def post_page(request: Request):
    return templates.TemplateResponse("blog.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
