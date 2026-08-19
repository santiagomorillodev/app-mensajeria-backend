from fastapi import FastAPI
from config import init_db
from routers import user, conversations, messages, post, socket, signaling
from fastapi.middleware.cors import CORSMiddleware


init_db()

app = FastAPI()


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://localhost:5173",
    "https://messagin-frontend.vercel.app",
    "https://messagin-backend.onrender.com",
    "https://messagin-frontend-git-main-santiagomorillodevs-projects.vercel.app",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(user)
app.include_router(conversations)
app.include_router(messages)
app.include_router(post)
app.include_router(socket)
app.include_router(signaling)

print("\n================ RUTAS REGISTRADAS ================\n")

for route in app.routes:
    print(
        f"PATH: {route.path} | "
        f"NAME: {route.name} | "
        f"TYPE: {type(route).__name__}"
    )

print("\n====================================================\n")


@app.get('/')
def root():
    return {'message': 'Api running'}