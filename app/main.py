from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from app.routers import auth, tasks, files, ws
from app.middlewares import log_requests, add_security_headers
from app.database import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(title="ToDo App", version="1.0")

templates = Jinja2Templates(directory="templates")

app.middleware("http")(log_requests)
app.middleware("http")(add_security_headers)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", name="login_page")
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", name="register_page")
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/tasks", name="tasks_page")
def tasks_page(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})

@app.get("/upload", name="upload_page")
def upload(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})