from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date
from enum import Enum
import jwt
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'chuflay_db')]

# Create the main app
app = FastAPI(title="Chuflay - Plataforma Educativa", version="1.0.0")

# Create API router
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SECRET_KEY = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

# Enums
class UserRole(str, Enum):
    ADMIN_GLOBAL = "admin_global"
    ADMIN_COLEGIO = "admin_colegio"
    PADRE = "padre"
    ESTUDIANTE = "estudiante"
    PROFESOR = "profesor"
    PROVEEDOR = "proveedor"

class ActivityVisibility(str, Enum):
    INTERNA = "interna"  # Solo estudiantes del colegio
    EXTERNA = "externa"  # Abierta al público
    MIXTA = "mixta"     # Estudiantes + externos

class ActivityStatus(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    REPROGRAMADA = "reprogramada"

class PaymentMethod(str, Enum):
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    EFECTIVO = "efectivo"

class InscriptionStatus(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    PAGO_PENDIENTE = "pago_pendiente"
    CANCELADA = "cancelada"

# Base Models
class BaseModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# User Models
class User(BaseModel):
    email: str
    hashed_password: str
    role: UserRole
    is_active: bool = True
    full_name: str
    colegio_id: Optional[str] = None
    
class UserCreate(BaseModel):
    email: str
    password: str
    role: UserRole
    full_name: str
    colegio_id: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    full_name: str
    is_active: bool
    colegio_id: Optional[str] = None

# Colegio Models
class Colegio(BaseModel):
    nombre: str
    rnc: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    email_oficial: Optional[str] = None
    director: Optional[str] = None
    estado: str = "activo"

class ColegioCreate(BaseModel):
    nombre: str
    rnc: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    email_oficial: Optional[str] = None
    director: Optional[str] = None

# Student Models
class Estudiante(BaseModel):
    nombre_completo: str
    fecha_nacimiento: date
    curso_grado: str
    colegio_id: str
    padre_id: Optional[str] = None
    foto_url: Optional[str] = None
    informacion_medica: Optional[Dict[str, Any]] = None

class EstudianteCreate(BaseModel):
    nombre_completo: str
    fecha_nacimiento: date
    curso_grado: str
    colegio_id: str
    padre_id: Optional[str] = None

# Activity Models
class Activity(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    fecha_inicio: datetime
    fecha_fin: datetime
    colegio_id: str
    cursos_participantes: List[str] = []
    cupo_maximo: Optional[int] = None
    costo_estudiante: float = 0.0
    materiales_requeridos: List[str] = []
    visibilidad: ActivityVisibility = ActivityVisibility.INTERNA
    estado: ActivityStatus = ActivityStatus.PENDIENTE
    responsable: Optional[str] = None
    metodos_pago: List[PaymentMethod] = []
    es_permanente: bool = False
    link_inscripcion: Optional[str] = None
    requiere_validacion_manual: bool = False
    galeria_urls: List[str] = []
    participantes_confirmados: int = 0

class ActivityCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    fecha_inicio: datetime
    fecha_fin: datetime
    cursos_participantes: List[str] = []
    cupo_maximo: Optional[int] = None
    costo_estudiante: float = 0.0
    materiales_requeridos: List[str] = []
    visibilidad: ActivityVisibility = ActivityVisibility.INTERNA
    responsable: Optional[str] = None
    metodos_pago: List[PaymentMethod] = []
    es_permanente: bool = False
    requiere_validacion_manual: bool = False

class ActivityUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    cursos_participantes: Optional[List[str]] = None
    cupo_maximo: Optional[int] = None
    costo_estudiante: Optional[float] = None
    materiales_requeridos: Optional[List[str]] = None
    visibilidad: Optional[ActivityVisibility] = None
    estado: Optional[ActivityStatus] = None
    responsable: Optional[str] = None
    metodos_pago: Optional[List[PaymentMethod]] = None

# Inscription Models
class Inscription(BaseModel):
    actividad_id: str
    estudiante_id: str
    padre_id: str
    colegio_id: str
    estado: InscriptionStatus = InscriptionStatus.PENDIENTE
    monto_pagado: float = 0.0
    metodo_pago_usado: Optional[PaymentMethod] = None
    fecha_pago: Optional[datetime] = None
    comentarios: Optional[str] = None

class InscriptionCreate(BaseModel):
    actividad_id: str
    estudiante_id: str
    comentarios: Optional[str] = None

# Helper functions
def hash_password(password: str) -> str:
    # Limit password length for bcrypt
    password = password[:72] if len(password) > 72 else password
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Limit password length for bcrypt
    plain_password = plain_password[:72] if len(plain_password) > 72 else plain_password
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow().timestamp() + 86400  # 24 hours
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_doc = await db.users.find_one({"id": user_id})
        if user_doc is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_doc)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth endpoints
@api_router.post("/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        full_name=user_data.full_name,
        colegio_id=user_data.colegio_id
    )
    
    await db.users.insert_one(user.dict())
    return UserResponse(**user.dict())

@api_router.post("/auth/login")
async def login_user(user_data: UserLogin):
    user_doc = await db.users.find_one({"email": user_data.email})
    if not user_doc or not verify_password(user_data.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user_doc["is_active"]:
        raise HTTPException(status_code=401, detail="User account is disabled")
    
    access_token = create_access_token({"sub": user_doc["id"], "role": user_doc["role"]})
    user_response = UserResponse(**user_doc)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response
    }

# Colegio endpoints
@api_router.post("/colegios", response_model=Colegio)
async def create_colegio(colegio_data: ColegioCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_GLOBAL, UserRole.ADMIN_COLEGIO]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    colegio = Colegio(**colegio_data.dict())
    await db.colegios.insert_one(colegio.dict())
    return colegio

@api_router.get("/colegios", response_model=List[Colegio])
async def get_colegios(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN_GLOBAL:
        colegios = await db.colegios.find().to_list(1000)
    else:
        colegios = await db.colegios.find({"id": current_user.colegio_id}).to_list(1000)
    
    return [Colegio(**colegio) for colegio in colegios]

# Student endpoints
@api_router.post("/estudiantes", response_model=Estudiante)
async def create_estudiante(estudiante_data: EstudianteCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.PADRE]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # If padre creating, set padre_id automatically
    if current_user.role == UserRole.PADRE:
        estudiante_data.padre_id = current_user.id
        estudiante_data.colegio_id = current_user.colegio_id
    
    estudiante = Estudiante(**estudiante_data.dict())
    await db.estudiantes.insert_one(estudiante.dict())
    return estudiante

@api_router.get("/estudiantes", response_model=List[Estudiante])
async def get_estudiantes(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.PADRE:
        estudiantes = await db.estudiantes.find({"padre_id": current_user.id}).to_list(1000)
    elif current_user.role == UserRole.ADMIN_COLEGIO:
        estudiantes = await db.estudiantes.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return [Estudiante(**estudiante) for estudiante in estudiantes]

# Activity endpoints
@api_router.post("/actividades", response_model=Activity)
async def create_activity(activity_data: ActivityCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.PROFESOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    activity = Activity(**activity_data.dict(), colegio_id=current_user.colegio_id)
    
    # Generate public link if external or mixed
    if activity.visibilidad in [ActivityVisibility.EXTERNA, ActivityVisibility.MIXTA]:
        activity.link_inscripcion = f"/inscripcion/{activity.id}"
    
    await db.actividades.insert_one(activity.dict())
    return activity

@api_router.get("/actividades", response_model=List[Activity])
async def get_activities(
    curso: Optional[str] = None,
    estado: Optional[ActivityStatus] = None,
    current_user: User = Depends(get_current_user)
):
    filter_query = {}
    
    if current_user.role in [UserRole.ADMIN_COLEGIO, UserRole.PROFESOR]:
        filter_query["colegio_id"] = current_user.colegio_id
    elif current_user.role == UserRole.PADRE:
        filter_query["colegio_id"] = current_user.colegio_id
        # Only show activities where visibility is not just external
        filter_query["visibilidad"] = {"$in": [ActivityVisibility.INTERNA, ActivityVisibility.MIXTA]}
    
    if curso:
        filter_query["cursos_participantes"] = curso
    if estado:
        filter_query["estado"] = estado
    
    activities = await db.actividades.find(filter_query).to_list(1000)
    return [Activity(**activity) for activity in activities]

@api_router.get("/actividades/{activity_id}", response_model=Activity)
async def get_activity(activity_id: str, current_user: User = Depends(get_current_user)):
    activity = await db.actividades.find_one({"id": activity_id})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check permissions
    if current_user.role in [UserRole.ADMIN_COLEGIO, UserRole.PROFESOR]:
        if activity["colegio_id"] != current_user.colegio_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif current_user.role == UserRole.PADRE:
        if activity["colegio_id"] != current_user.colegio_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return Activity(**activity)

@api_router.put("/actividades/{activity_id}", response_model=Activity)
async def update_activity(
    activity_id: str,
    update_data: ActivityUpdate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.PROFESOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    activity = await db.actividades.find_one({"id": activity_id, "colegio_id": current_user.colegio_id})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Update only provided fields
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.actividades.update_one({"id": activity_id}, {"$set": update_dict})
    updated_activity = await db.actividades.find_one({"id": activity_id})
    return Activity(**updated_activity)

@api_router.delete("/actividades/{activity_id}")
async def delete_activity(activity_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_COLEGIO]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.actividades.delete_one({"id": activity_id, "colegio_id": current_user.colegio_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {"message": "Activity deleted successfully"}

# Inscription endpoints
@api_router.post("/inscripciones", response_model=Inscription)
async def create_inscription(inscription_data: InscriptionCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PADRE:
        raise HTTPException(status_code=403, detail="Only parents can inscribe students")
    
    # Verify student belongs to current user
    estudiante = await db.estudiantes.find_one({
        "id": inscription_data.estudiante_id,
        "padre_id": current_user.id
    })
    if not estudiante:
        raise HTTPException(status_code=404, detail="Student not found or not authorized")
    
    # Verify activity exists and is available
    activity = await db.actividades.find_one({"id": inscription_data.actividad_id})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check if already inscribed
    existing_inscription = await db.inscripciones.find_one({
        "actividad_id": inscription_data.actividad_id,
        "estudiante_id": inscription_data.estudiante_id
    })
    if existing_inscription:
        raise HTTPException(status_code=400, detail="Student already inscribed")
    
    # Check cupo
    if activity.get("cupo_maximo"):
        current_inscriptions = await db.inscripciones.count_documents({
            "actividad_id": inscription_data.actividad_id,
            "estado": {"$in": [InscriptionStatus.CONFIRMADA, InscriptionStatus.PAGO_PENDIENTE]}
        })
        if current_inscriptions >= activity["cupo_maximo"]:
            raise HTTPException(status_code=400, detail="Activity is full")
    
    inscription = Inscription(
        **inscription_data.dict(),
        padre_id=current_user.id,
        colegio_id=estudiante["colegio_id"],
        estado=InscriptionStatus.PAGO_PENDIENTE if activity["costo_estudiante"] > 0 else InscriptionStatus.CONFIRMADA
    )
    
    await db.inscripciones.insert_one(inscription.dict())
    return inscription

@api_router.get("/inscripciones", response_model=List[Inscription])
async def get_inscriptions(current_user: User = Depends(get_current_user)):
    filter_query = {}
    
    if current_user.role == UserRole.PADRE:
        filter_query["padre_id"] = current_user.id
    elif current_user.role in [UserRole.ADMIN_COLEGIO, UserRole.PROFESOR]:
        filter_query["colegio_id"] = current_user.colegio_id
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    inscriptions = await db.inscripciones.find(filter_query).to_list(1000)
    return [Inscription(**inscription) for inscription in inscriptions]

# Dashboard endpoints
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN_COLEGIO:
        stats = {
            "total_actividades": await db.actividades.count_documents({"colegio_id": current_user.colegio_id}),
            "actividades_activas": await db.actividades.count_documents({
                "colegio_id": current_user.colegio_id,
                "estado": ActivityStatus.CONFIRMADA
            }),
            "total_inscripciones": await db.inscripciones.count_documents({"colegio_id": current_user.colegio_id}),
            "total_estudiantes": await db.estudiantes.count_documents({"colegio_id": current_user.colegio_id})
        }
    elif current_user.role == UserRole.PADRE:
        mis_estudiantes = await db.estudiantes.find({"padre_id": current_user.id}).to_list(1000)
        stats = {
            "mis_hijos": len(mis_estudiantes),
            "inscripciones_activas": await db.inscripciones.count_documents({
                "padre_id": current_user.id,
                "estado": {"$in": [InscriptionStatus.CONFIRMADA, InscriptionStatus.PAGO_PENDIENTE]}
            }),
            "pagos_pendientes": await db.inscripciones.count_documents({
                "padre_id": current_user.id,
                "estado": InscriptionStatus.PAGO_PENDIENTE
            })
        }
    else:
        stats = {"message": "Dashboard not available for this role"}
    
    return stats

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "Chuflay API - Módulo de Actividades v1.0"}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()