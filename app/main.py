from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException, status, WebSocket, WebSocketDisconnect, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import json
from datetime import datetime
from typing import Dict, Optional


# Припускаємо, що app, models, utils, database існують
from app import models, utils, database


# Database

models.Base.metadata.create_all(bind=database.engine)


# App init

app = FastAPI(title="ToDo App", version="1.0")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Uploads folder

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# Connection Manager for WebSocket Chat
class ConnectionManager:
    def __init__(self):
        # Словник для зберігання активних з'єднань: {user_email: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_email: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_email] = websocket

    def disconnect(self, user_email: str):
        if user_email in self.active_connections:
            del self.active_connections[user_email]

    async def send_personal_message(self, message: str, receiver_email: str) -> bool:
        if receiver_email in self.active_connections:
            try:
                await self.active_connections[receiver_email].send_text(message)
                return True
            except RuntimeError:
                # Обробка випадку, коли з'єднання закрилося під час відправки
                self.disconnect(receiver_email)
                return False
        return False


manager = ConnectionManager()


# Home page

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Auth routes

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, db: Session = Depends(database.get_db)):
    form = await request.form()
    username = form.get("username")
    email = form.get("email")
    password = form.get("password")

    if not username or not email or not password:
        return templates.TemplateResponse("register.html", {"request": request, "error": "All fields required"})

    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})

    hashed_pw = utils.hash_password(password)
    new_user = models.User(username=username, email=email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return templates.TemplateResponse("login.html", {"request": request, "message": "Registered successfully. Login now!"})

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, db: Session = Depends(database.get_db)):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not utils.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

    # Створюємо токен (JWT)
    token = utils.create_access_token({"sub": user.email})
    response = RedirectResponse(url="/tasks", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

# Tasks routes

@app.get("/tasks")
def tasks_page(request: Request, db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user})

@app.post("/tasks")
async def add_task(request: Request, db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    form = await request.form()
    task_title = form.get("task")
    if task_title:
        new_task = models.Task(title=task_title, owner_id=user.id)
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
    tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user})

@app.get("/delete/{task_id}")
def delete_task(task_id: int, request: Request, db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user.id).first()
    if task:
        db.delete(task)
        db.commit()
    tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user})

@app.get("/complete/{task_id}")
def complete_task(task_id: int, request: Request, db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user.id).first()
    if task:
        task.status = "done"
        db.commit()
    tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user})

@app.get("/uncomplete/{task_id}")
def uncomplete_task(task_id: int, request: Request, db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user.id).first()
    if task:
        task.status = "new"
        db.commit()
    tasks = db.query(models.Task).filter(models.Task.owner_id == user.id).all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user})


@app.get("/files/{task_id}")
async def get_files(
        task_id: int,
        db: Session = Depends(database.get_db),
        user=Depends(utils.get_current_user)
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.owner_id == user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    return [{"filename": f.filename, "id": f.id} for f in task.files]

# File upload routes

@app.post("/upload")
async def upload_file(
        task_id: int = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(database.get_db),
        user=Depends(utils.get_current_user)
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.owner_id == user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or you don't have access to it."
        )

    unique_filename = f"{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}"
        )
    finally:
        file.file.close()

    new_file = models.File(
        filename=file.filename,
        file_path=str(file_path),
        task_id=task.id
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return {
        "filename": new_file.filename,
        "id": new_file.id
    }



# WebSocket routes


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):

    # SENDER's ID is expected as a query parameter (e.g., ?email=user@example.com)
    sender_email: Optional[str] = websocket.query_params.get("email")

    if not sender_email:
        # Заборона підключення без ідентифікатора
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 1. Реєструємо з'єднання
    await manager.connect(sender_email, websocket)

    try:
        # 2. Надсилаємо підтвердження про реєстрацію
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": f"Ви підключені як: {sender_email}. Введіть email отримувача для початку."
        }))

        while True:
            # 3. Отримуємо повідомлення від відправника
            data = await websocket.receive_text()
            message_json = json.loads(data)

            # Очікуємо структуру: {username: recipient_id, message: content}
            recipient_email = message_json.get("username")
            content = message_json.get("message")

            if recipient_email and content:
                # Форматуємо повідомлення для отримувача
                formatted_message = json.dumps({
                    "type": "received_message",
                    "sender": sender_email,
                    "content": content
                })

                # Надсилаємо повідомлення отримувачу
                sent_success = await manager.send_personal_message(
                    message=formatted_message,
                    receiver_email=recipient_email
                )

                # Надсилаємо підтвердження відправнику (щоб він побачив своє повідомлення)
                if not sent_success:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Помилка: Користувач {recipient_email} не знайдений або відключений."
                    }))

                # Надсилаємо власне повідомлення відправнику
                await websocket.send_text(json.dumps({
                    "type": "own_message",
                    "recipient": recipient_email,
                    "content": content
                }))

            else:
                await websocket.send_text(json.dumps({"type": "error", "message": "Невірний формат повідомлення."}))

    except WebSocketDisconnect:
        manager.disconnect(sender_email)
    except json.JSONDecodeError:
        await websocket.send_text(json.dumps({"type": "error", "message": "Невірний формат: очікується JSON."}))