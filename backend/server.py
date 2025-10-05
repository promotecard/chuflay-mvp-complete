from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
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
import shutil

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

# Create uploads directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

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

class PaymentStatus(str, Enum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    REEMBOLSADO = "reembolsado"

class SubscriptionPlan(str, Enum):
    BASICO = "basico"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    CANCELADO = "cancelado"
    VENCIDO = "vencido"

class MessageType(str, Enum):
    CIRCULAR = "circular"
    COMUNICADO = "comunicado"
    ANUNCIO = "anuncio"
    NOTIFICACION = "notificacion"

class MessagePriority(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"

class MessageStatus(str, Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    PROGRAMADO = "programado"
    ARCHIVADO = "archivado"

class NotificationStatus(str, Enum):
    NO_LEIDA = "no_leida"
    LEIDA = "leida"
    ARCHIVADA = "archivada"

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
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    plan_suscripcion: SubscriptionPlan = SubscriptionPlan.BASICO
    fecha_vencimiento: Optional[datetime] = None
    configuracion: Optional[Dict[str, Any]] = None

class ColegioCreate(BaseModel):
    nombre: str
    rnc: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    email_oficial: Optional[str] = None
    director: Optional[str] = None
    plan_suscripcion: SubscriptionPlan = SubscriptionPlan.BASICO

class ColegioUpdate(BaseModel):
    nombre: Optional[str] = None
    rnc: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    email_oficial: Optional[str] = None
    director: Optional[str] = None
    estado: Optional[str] = None
    plan_suscripcion: Optional[SubscriptionPlan] = None
    fecha_vencimiento: Optional[datetime] = None

# Subscription Models
class Subscription(BaseModel):
    colegio_id: str
    plan: SubscriptionPlan
    estado: SubscriptionStatus = SubscriptionStatus.ACTIVO
    fecha_inicio: datetime = Field(default_factory=datetime.utcnow)
    fecha_vencimiento: datetime
    precio_mensual: float
    caracteristicas: List[str] = []
    limite_estudiantes: Optional[int] = None
    limite_actividades: Optional[int] = None

class SubscriptionCreate(BaseModel):
    colegio_id: str
    plan: SubscriptionPlan
    meses: int = 12
    precio_mensual: float

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
    colegio_id: Optional[str] = None
    padre_id: Optional[str] = None

# Custom Form Field Models
class FormField(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    tipo: str  # text, email, number, select, textarea, checkbox, date
    requerido: bool = False
    opciones: Optional[List[str]] = None  # Para campos select
    placeholder: Optional[str] = None
    validacion: Optional[Dict[str, Any]] = None

# Activity Models con campos personalizados
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
    # Nuevos campos
    imagen_actividad: Optional[str] = None  # URL de la imagen principal
    campos_personalizados: List[FormField] = []  # Campos adicionales tipo Google Forms
    ubicacion: Optional[str] = None
    instructor: Optional[str] = None
    edad_minima: Optional[int] = None
    edad_maxima: Optional[int] = None

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
    # Nuevos campos
    imagen_actividad: Optional[str] = None
    campos_personalizados: List[FormField] = []
    ubicacion: Optional[str] = None
    instructor: Optional[str] = None
    edad_minima: Optional[int] = None
    edad_maxima: Optional[int] = None

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
    imagen_actividad: Optional[str] = None
    campos_personalizados: Optional[List[FormField]] = None
    ubicacion: Optional[str] = None
    instructor: Optional[str] = None

# Inscription Models con campos personalizados
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
    respuestas_campos: Optional[Dict[str, Any]] = None  # Respuestas a campos personalizados

class InscriptionCreate(BaseModel):
    actividad_id: str
    estudiante_id: str
    comentarios: Optional[str] = None
    respuestas_campos: Optional[Dict[str, Any]] = None

# Payment Models
class Payment(BaseModel):
    inscripcion_id: str
    actividad_id: str
    estudiante_id: str
    padre_id: str
    monto: float
    metodo_pago: PaymentMethod
    estado: PaymentStatus = PaymentStatus.PENDIENTE
    referencia_pago: Optional[str] = None
    datos_pago: Optional[Dict[str, Any]] = None
    fecha_procesado: Optional[datetime] = None
    notas: Optional[str] = None

class PaymentCreate(BaseModel):
    inscripcion_id: str
    metodo_pago: PaymentMethod
    datos_pago: Optional[Dict[str, Any]] = None
    notas: Optional[str] = None

class PaymentUpdate(BaseModel):
    estado: Optional[PaymentStatus] = None
    referencia_pago: Optional[str] = None
    datos_pago: Optional[Dict[str, Any]] = None
    notas: Optional[str] = None

# Notification Models  
class Notification(BaseModel):
    titulo: str
    mensaje: str
    tipo: str = "general"
    destinatario_id: str
    destinatario_role: UserRole
    leida: bool = False
    colegio_id: str
    actividad_id: Optional[str] = None
    inscripcion_id: Optional[str] = None
    pago_id: Optional[str] = None

class NotificationCreate(BaseModel):
    titulo: str
    mensaje: str
    tipo: str = "general"
    destinatario_id: str
    destinatario_role: UserRole
    actividad_id: Optional[str] = None
    inscripcion_id: Optional[str] = None
    pago_id: Optional[str] = None

# Communication Models
class Circular(BaseModel):
    titulo: str
    contenido: str
    colegio_id: str
    autor_id: str
    dirigida_a: List[UserRole] = []  # Lista de roles a los que va dirigida
    cursos_objetivo: List[str] = []  # Cursos específicos
    fecha_publicacion: datetime = Field(default_factory=datetime.utcnow)
    adjuntos: List[str] = []
    prioridad: str = "normal"  # normal, alta, urgente
    requiere_confirmacion: bool = False

class CircularCreate(BaseModel):
    titulo: str
    contenido: str
    dirigida_a: List[UserRole] = []
    cursos_objetivo: List[str] = []
    adjuntos: List[str] = []
    prioridad: str = "normal"
    requiere_confirmacion: bool = False

# Enhanced Communication Models
class Message(BaseModel):
    titulo: str
    contenido: str
    tipo: MessageType
    prioridad: MessagePriority = MessagePriority.MEDIA
    estado: MessageStatus = MessageStatus.BORRADOR
    colegio_id: str
    autor_id: str
    autor_nombre: str
    dirigida_a: List[UserRole] = []
    usuarios_especificos: List[str] = []  # IDs de usuarios específicos
    cursos_objetivo: List[str] = []
    adjuntos: List[str] = []
    fecha_programada: Optional[datetime] = None
    fecha_enviado: Optional[datetime] = None
    requiere_confirmacion: bool = False
    total_destinatarios: int = 0
    total_leidos: int = 0

class MessageCreate(BaseModel):
    titulo: str
    contenido: str
    tipo: MessageType
    prioridad: MessagePriority = MessagePriority.MEDIA
    dirigida_a: List[UserRole] = []
    usuarios_especificos: List[str] = []
    cursos_objetivo: List[str] = []
    adjuntos: List[str] = []
    fecha_programada: Optional[datetime] = None
    requiere_confirmacion: bool = False

class MessageUpdate(BaseModel):
    titulo: Optional[str] = None
    contenido: Optional[str] = None
    prioridad: Optional[MessagePriority] = None
    estado: Optional[MessageStatus] = None
    fecha_programada: Optional[datetime] = None

class UserNotification(BaseModel):
    mensaje_id: str
    usuario_id: str
    usuario_email: str
    usuario_nombre: str
    estado: NotificationStatus = NotificationStatus.NO_LEIDA
    fecha_leido: Optional[datetime] = None
    confirmado: bool = False
    fecha_confirmacion: Optional[datetime] = None

class NotificationRead(BaseModel):
    confirmacion: bool = False

class CommunicationStats(BaseModel):
    total_mensajes: int
    mensajes_enviados: int
    mensajes_borradores: int
    mensajes_programados: int
    tasa_lectura_promedio: float
    mensajes_por_tipo: Dict[str, int]

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
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

async def create_notification(notification_data: NotificationCreate, colegio_id: str):
    """Helper para crear notificaciones"""
    notification = Notification(**notification_data.dict(), colegio_id=colegio_id)
    await db.notifications.insert_one(notification.dict())
    return notification

# File Upload endpoints
@api_router.post("/upload/imagen")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Subir imagen para actividades"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generar nombre único
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Retornar URL pública
    return {"url": f"/uploads/{unique_filename}"}

# Auth endpoints (mantener igual)
@api_router.post("/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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

# ADMIN GLOBAL ENDPOINTS
@api_router.get("/global/colegios", response_model=List[Colegio])
async def get_all_colegios(current_user: User = Depends(get_current_user)):
    """Ver todos los colegios (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can access this")
    
    colegios = await db.colegios.find().to_list(1000)
    return [Colegio(**colegio) for colegio in colegios]

@api_router.post("/global/colegios", response_model=Colegio)
async def create_colegio_global(colegio_data: ColegioCreate, current_user: User = Depends(get_current_user)):
    """Crear colegio (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can create colleges")
    
    colegio = Colegio(**colegio_data.dict())
    await db.colegios.insert_one(colegio.dict())
    return colegio

@api_router.put("/global/colegios/{colegio_id}", response_model=Colegio)
async def update_colegio_global(colegio_id: str, update_data: ColegioUpdate, current_user: User = Depends(get_current_user)):
    """Actualizar colegio (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can update colleges")
    
    # First, get the original college to ensure it exists
    original_college = await db.colegios.find_one({"id": colegio_id})
    if not original_college:
        raise HTTPException(status_code=404, detail="College not found")
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.colegios.update_one({"id": colegio_id}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="College not found during update")
    
    # Apply the updates to the original data and return
    for key, value in update_dict.items():
        original_college[key] = value
    
    return Colegio(**original_college)

@api_router.get("/global/usuarios", response_model=List[UserResponse])
async def get_all_users(current_user: User = Depends(get_current_user)):
    """Ver todos los usuarios (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can access this")
    
    users = await db.users.find().to_list(1000)
    return [UserResponse(**user) for user in users]

@api_router.post("/global/impersonate/{user_id}")
async def impersonate_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Impersonar usuario (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can impersonate users")
    
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Crear token para el usuario objetivo
    access_token = create_access_token({"sub": target_user["id"], "role": target_user["role"], "impersonated_by": current_user.id})
    user_response = UserResponse(**target_user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response,
        "impersonated": True,
        "impersonated_by": current_user.full_name
    }

@api_router.get("/global/estadisticas")
async def get_global_stats(current_user: User = Depends(get_current_user)):
    """Estadísticas globales (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can access global stats")
    
    stats = {
        "total_colegios": await db.colegios.count_documents({}),
        "colegios_activos": await db.colegios.count_documents({"estado": "activo"}),
        "total_usuarios": await db.users.count_documents({}),
        "total_estudiantes": await db.estudiantes.count_documents({}),
        "total_actividades": await db.actividades.count_documents({}),
        "total_inscripciones": await db.inscripciones.count_documents({}),
        "total_pagos": await db.pagos.count_documents({}),
    }
    
    # Estadísticas por plan
    planes_stats = {}
    for plan in SubscriptionPlan:
        planes_stats[f"colegios_{plan.value}"] = await db.colegios.count_documents({"plan_suscripcion": plan.value})
    
    return {**stats, **planes_stats}

# Suscriptions endpoints
@api_router.post("/global/suscripciones", response_model=Subscription)
async def create_subscription(subscription_data: SubscriptionCreate, current_user: User = Depends(get_current_user)):
    """Crear suscripción (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can create subscriptions")
    
    # Calcular fecha de vencimiento
    from datetime import timedelta
    fecha_vencimiento = datetime.utcnow() + timedelta(days=subscription_data.meses * 30)
    
    # Definir características por plan
    caracteristicas_por_plan = {
        SubscriptionPlan.BASICO: ["Hasta 100 estudiantes", "Actividades básicas", "Soporte por email"],
        SubscriptionPlan.PREMIUM: ["Hasta 500 estudiantes", "Actividades avanzadas", "Reportes", "Soporte prioritario"],
        SubscriptionPlan.ENTERPRISE: ["Estudiantes ilimitados", "Todas las funcionalidades", "API access", "Soporte 24/7"]
    }
    
    subscription = Subscription(
        colegio_id=subscription_data.colegio_id,
        plan=subscription_data.plan,
        fecha_vencimiento=fecha_vencimiento,
        precio_mensual=subscription_data.precio_mensual,
        caracteristicas=caracteristicas_por_plan.get(subscription_data.plan, []),
        limite_estudiantes=100 if subscription_data.plan == SubscriptionPlan.BASICO else 500 if subscription_data.plan == SubscriptionPlan.PREMIUM else None
    )
    
    await db.subscriptions.insert_one(subscription.dict())
    
    # Actualizar el colegio con el plan
    await db.colegios.update_one(
        {"id": subscription_data.colegio_id},
        {"$set": {"plan_suscripcion": subscription_data.plan, "fecha_vencimiento": fecha_vencimiento}}
    )
    
    return subscription

@api_router.get("/global/suscripciones", response_model=List[Subscription])
async def get_all_subscriptions(current_user: User = Depends(get_current_user)):
    """Ver todas las suscripciones (Solo Admin Global)"""
    if current_user.role != UserRole.ADMIN_GLOBAL:
        raise HTTPException(status_code=403, detail="Only global admins can access subscriptions")
    
    subscriptions = await db.subscriptions.find().to_list(1000)
    return [Subscription(**sub) for sub in subscriptions]

# Colegio endpoints (mantener y mejorar)
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

# Resto de endpoints (mantener igual pero con mejoras)
# [Todos los endpoints anteriores de estudiantes, actividades, inscripciones, pagos, notificaciones, etc.]
# Por brevedad, mantengo la estructura anterior pero con las mejoras mencionadas

# Student endpoints (mantener igual)
@api_router.post("/estudiantes", response_model=Estudiante)
async def create_estudiante(estudiante_data: EstudianteCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.PADRE]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if current_user.role == UserRole.PADRE:
        estudiante_data.padre_id = current_user.id
        estudiante_data.colegio_id = current_user.colegio_id
    
    estudiante = Estudiante(**estudiante_data.dict())
    estudiante_dict = estudiante.dict()
    estudiante_dict['fecha_nacimiento'] = estudiante_dict['fecha_nacimiento'].isoformat()
    
    await db.estudiantes.insert_one(estudiante_dict)
    return estudiante

@api_router.get("/estudiantes", response_model=List[Estudiante])
async def get_estudiantes(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.PADRE:
        estudiantes = await db.estudiantes.find({"padre_id": current_user.id}).to_list(1000)
    elif current_user.role == UserRole.ADMIN_COLEGIO:
        estudiantes = await db.estudiantes.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = []
    for estudiante in estudiantes:
        if isinstance(estudiante['fecha_nacimiento'], str):
            estudiante['fecha_nacimiento'] = datetime.fromisoformat(estudiante['fecha_nacimiento']).date()
        result.append(Estudiante(**estudiante))
    
    return result

# Activity endpoints mejorados
@api_router.post("/actividades", response_model=Activity)
async def create_activity(activity_data: ActivityCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.PROFESOR]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    activity = Activity(**activity_data.dict(), colegio_id=current_user.colegio_id)
    
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
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.actividades.update_one({"id": activity_id}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    updated_activity = await db.actividades.find_one({"id": activity_id})
    if not updated_activity:
        raise HTTPException(status_code=404, detail="Activity not found after update")
    
    return Activity(**updated_activity)

@api_router.delete("/actividades/{activity_id}")
async def delete_activity(activity_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN_COLEGIO]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.actividades.delete_one({"id": activity_id, "colegio_id": current_user.colegio_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {"message": "Activity deleted successfully"}

# Inscription endpoints mejorados con campos personalizados
@api_router.post("/inscripciones", response_model=Inscription)
async def create_inscription(inscription_data: InscriptionCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PADRE:
        raise HTTPException(status_code=403, detail="Only parents can inscribe students")
    
    estudiante = await db.estudiantes.find_one({
        "id": inscription_data.estudiante_id,
        "padre_id": current_user.id
    })
    if not estudiante:
        raise HTTPException(status_code=404, detail="Student not found or not authorized")
    
    activity = await db.actividades.find_one({"id": inscription_data.actividad_id})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    existing_inscription = await db.inscripciones.find_one({
        "actividad_id": inscription_data.actividad_id,
        "estudiante_id": inscription_data.estudiante_id
    })
    if existing_inscription:
        raise HTTPException(status_code=400, detail="Student already inscribed")
    
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
    
    await create_notification(
        NotificationCreate(
            titulo="Inscripción Realizada",
            mensaje=f"Tu hijo ha sido inscrito en '{activity['nombre']}'" + 
                   (f". Monto a pagar: ${activity['costo_estudiante']}" if activity["costo_estudiante"] > 0 else ""),
            tipo="inscripcion",
            destinatario_id=current_user.id,
            destinatario_role=UserRole.PADRE,
            actividad_id=inscription_data.actividad_id,
            inscripcion_id=inscription.id
        ),
        current_user.colegio_id
    )
    
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

# Mantener todos los demás endpoints de pagos, notificaciones, dashboard, etc.
# (Por brevedad del código, mantengo la misma estructura pero con las mejoras mencionadas)

# Payment endpoints (mantener igual)
@api_router.post("/pagos", response_model=Payment)
async def create_payment(payment_data: PaymentCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PADRE:
        raise HTTPException(status_code=403, detail="Only parents can make payments")
    
    inscription = await db.inscripciones.find_one({
        "id": payment_data.inscripcion_id,
        "padre_id": current_user.id
    })
    if not inscription:
        raise HTTPException(status_code=404, detail="Inscription not found")
    
    activity = await db.actividades.find_one({"id": inscription["actividad_id"]})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    existing_payment = await db.pagos.find_one({"inscripcion_id": payment_data.inscripcion_id})
    if existing_payment:
        raise HTTPException(status_code=400, detail="Payment already exists for this inscription")
    
    payment = Payment(
        inscripcion_id=payment_data.inscripcion_id,
        actividad_id=inscription["actividad_id"],
        estudiante_id=inscription["estudiante_id"],
        padre_id=current_user.id,
        monto=activity["costo_estudiante"],
        metodo_pago=payment_data.metodo_pago,
        datos_pago=payment_data.datos_pago or {},
        notas=payment_data.notas,
        referencia_pago=f"PAY-{uuid.uuid4().hex[:8].upper()}"
    )
    
    await db.pagos.insert_one(payment.dict())
    
    if payment_data.metodo_pago == PaymentMethod.EFECTIVO:
        payment.estado = PaymentStatus.PENDIENTE
        await db.pagos.update_one({"id": payment.id}, {"$set": {"estado": PaymentStatus.PENDIENTE}})
        notification_msg = f"Pago en efectivo registrado. Entrega ${activity['costo_estudiante']} en el colegio con referencia {payment.referencia_pago}"
        
    elif payment_data.metodo_pago == PaymentMethod.TRANSFERENCIA:
        payment.estado = PaymentStatus.PENDIENTE
        await db.pagos.update_one({"id": payment.id}, {"$set": {"estado": PaymentStatus.PENDIENTE}})
        notification_msg = f"Pago por transferencia registrado. Envía ${activity['costo_estudiante']} con referencia {payment.referencia_pago}"
        
    else:  # TARJETA
        payment.estado = PaymentStatus.COMPLETADO
        payment.fecha_procesado = datetime.utcnow()
        await db.pagos.update_one({"id": payment.id}, {"$set": {
            "estado": PaymentStatus.COMPLETADO,
            "fecha_procesado": datetime.utcnow()
        }})
        
        await db.inscripciones.update_one(
            {"id": payment_data.inscripcion_id},
            {"$set": {
                "estado": InscriptionStatus.CONFIRMADA,
                "monto_pagado": activity["costo_estudiante"],
                "metodo_pago_usado": payment_data.metodo_pago,
                "fecha_pago": datetime.utcnow()
            }}
        )
        
        notification_msg = f"¡Pago completado! Tu hijo está confirmado en '{activity['nombre']}'"
    
    await create_notification(
        NotificationCreate(
            titulo="Pago Procesado",
            mensaje=notification_msg,
            tipo="pago",
            destinatario_id=current_user.id,
            destinatario_role=UserRole.PADRE,
            actividad_id=inscription["actividad_id"],
            inscripcion_id=payment_data.inscripcion_id,
            pago_id=payment.id
        ),
        current_user.colegio_id
    )
    
    return payment

@api_router.get("/pagos", response_model=List[Payment])
async def get_payments(current_user: User = Depends(get_current_user)):
    filter_query = {}
    
    if current_user.role == UserRole.PADRE:
        filter_query["padre_id"] = current_user.id
    elif current_user.role in [UserRole.ADMIN_COLEGIO]:
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        filter_query["inscripcion_id"] = {"$in": inscripcion_ids}
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    payments = await db.pagos.find(filter_query).to_list(1000)
    return [Payment(**payment) for payment in payments]

@api_router.put("/pagos/{payment_id}/confirmar")
async def confirm_payment(payment_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN_COLEGIO:
        raise HTTPException(status_code=403, detail="Only administrators can confirm payments")
    
    payment = await db.pagos.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    inscription = await db.inscripciones.find_one({
        "id": payment["inscripcion_id"],
        "colegio_id": current_user.colegio_id
    })
    if not inscription:
        raise HTTPException(status_code=403, detail="Payment not found in your college")
    
    await db.pagos.update_one(
        {"id": payment_id},
        {"$set": {
            "estado": PaymentStatus.COMPLETADO,
            "fecha_procesado": datetime.utcnow()
        }}
    )
    
    activity = await db.actividades.find_one({"id": inscription["actividad_id"]})
    await db.inscripciones.update_one(
        {"id": payment["inscripcion_id"]},
        {"$set": {
            "estado": InscriptionStatus.CONFIRMADA,
            "monto_pagado": payment["monto"],
            "metodo_pago_usado": payment["metodo_pago"],
            "fecha_pago": datetime.utcnow()
        }}
    )
    
    await create_notification(
        NotificationCreate(
            titulo="¡Pago Confirmado!",
            mensaje=f"Tu pago ha sido confirmado. Tu hijo está inscrito en '{activity['nombre']}'",
            tipo="pago",
            destinatario_id=payment["padre_id"],
            destinatario_role=UserRole.PADRE,
            actividad_id=payment["actividad_id"],
            inscripcion_id=payment["inscripcion_id"],
            pago_id=payment_id
        ),
        current_user.colegio_id
    )
    
    return {"message": "Payment confirmed successfully"}

# Notification endpoints (mantener igual)
@api_router.get("/notificaciones", response_model=List[Notification])
async def get_notifications(current_user: User = Depends(get_current_user)):
    notifications = await db.notifications.find({
        "destinatario_id": current_user.id
    }).sort("created_at", -1).to_list(50)
    
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notificaciones/{notification_id}/leer")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    result = await db.notifications.update_one(
        {"id": notification_id, "destinatario_id": current_user.id},
        {"$set": {"leida": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}

# Communication endpoints
@api_router.post("/circulares", response_model=Circular)
async def create_circular(circular_data: CircularCreate, current_user: User = Depends(get_current_user)):
    """Crear circular (Solo Admin Colegio)"""
    if current_user.role != UserRole.ADMIN_COLEGIO:
        raise HTTPException(status_code=403, detail="Only college admins can create circulars")
    
    circular = Circular(
        **circular_data.dict(),
        colegio_id=current_user.colegio_id,
        autor_id=current_user.id
    )
    
    await db.circulares.insert_one(circular.dict())
    
    # Crear notificaciones para los destinatarios
    destinatarios_query = {}
    if circular_data.dirigida_a:
        destinatarios_query["role"] = {"$in": circular_data.dirigida_a}
    
    if current_user.colegio_id:
        destinatarios_query["colegio_id"] = current_user.colegio_id
    
    destinatarios = await db.users.find(destinatarios_query).to_list(1000)
    
    for destinatario in destinatarios:
        await create_notification(
            NotificationCreate(
                titulo=f"Nueva Circular: {circular.titulo}",
                mensaje=f"Se ha publicado una nueva circular. Prioridad: {circular.prioridad}",
                tipo="comunicado",
                destinatario_id=destinatario["id"],
                destinatario_role=UserRole(destinatario["role"])
            ),
            current_user.colegio_id
        )
    
    return circular

@api_router.get("/circulares", response_model=List[Circular])
async def get_circulares(current_user: User = Depends(get_current_user)):
    """Obtener circulares"""
    filter_query = {"colegio_id": current_user.colegio_id}
    
    if current_user.role != UserRole.ADMIN_COLEGIO:
        # Los no-admin solo ven las dirigidas a su rol
        filter_query["dirigida_a"] = {"$in": [current_user.role]}
    
    circulares = await db.circulares.find(filter_query).sort("fecha_publicacion", -1).to_list(100)
    return [Circular(**circular) for circular in circulares]

# Dashboard endpoints mejorados
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN_GLOBAL:
        # Estadísticas globales
        return await get_global_stats(current_user)
    
    elif current_user.role == UserRole.ADMIN_COLEGIO:
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        
        pagos_completados = await db.pagos.count_documents({
            "inscripcion_id": {"$in": inscripcion_ids},
            "estado": PaymentStatus.COMPLETADO
        })
        pagos_pendientes = await db.pagos.count_documents({
            "inscripcion_id": {"$in": inscripcion_ids},
            "estado": PaymentStatus.PENDIENTE
        })
        
        pagos_completados_docs = await db.pagos.find({
            "inscripcion_id": {"$in": inscripcion_ids},
            "estado": PaymentStatus.COMPLETADO
        }).to_list(1000)
        ingresos_totales = sum(p.get("monto", 0) for p in pagos_completados_docs)
        
        stats = {
            "total_actividades": await db.actividades.count_documents({"colegio_id": current_user.colegio_id}),
            "actividades_activas": await db.actividades.count_documents({
                "colegio_id": current_user.colegio_id,
                "estado": ActivityStatus.CONFIRMADA
            }),
            "total_inscripciones": len(inscripciones),
            "total_estudiantes": await db.estudiantes.count_documents({"colegio_id": current_user.colegio_id}),
            "pagos_completados": pagos_completados,
            "pagos_pendientes": pagos_pendientes,
            "ingresos_totales": f"${ingresos_totales:,.2f}"
        }
    
    elif current_user.role == UserRole.PADRE:
        mis_estudiantes = await db.estudiantes.find({"padre_id": current_user.id}).to_list(1000)
        mis_inscripciones = await db.inscripciones.find({"padre_id": current_user.id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in mis_inscripciones]
        
        mis_pagos = await db.pagos.find({"inscripcion_id": {"$in": inscripcion_ids}}).to_list(1000)
        pagos_completados = len([p for p in mis_pagos if p["estado"] == PaymentStatus.COMPLETADO])
        pagos_pendientes = len([p for p in mis_pagos if p["estado"] == PaymentStatus.PENDIENTE])
        
        stats = {
            "mis_hijos": len(mis_estudiantes),
            "inscripciones_activas": await db.inscripciones.count_documents({
                "padre_id": current_user.id,
                "estado": {"$in": [InscriptionStatus.CONFIRMADA, InscriptionStatus.PAGO_PENDIENTE]}
            }),
            "pagos_pendientes": pagos_pendientes,
            "pagos_completados": pagos_completados
        }
    else:
        stats = {"message": "Dashboard not available for this role"}
    
    return stats

# Reports endpoints
@api_router.get("/reportes/pagos")
async def get_payment_reports(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN_COLEGIO:
        raise HTTPException(status_code=403, detail="Only administrators can access reports")
    
    inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    inscripcion_ids = [i["id"] for i in inscripciones]
    
    pagos = await db.pagos.find({"inscripcion_id": {"$in": inscripcion_ids}}).to_list(1000)
    
    actividades = await db.actividades.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    estudiantes = await db.estudiantes.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    
    actividades_map = {a["id"]: a for a in actividades}
    estudiantes_map = {e["id"]: e for e in estudiantes}
    inscripciones_map = {i["id"]: i for i in inscripciones}
    
    pagos_enriquecidos = []
    for pago in pagos:
        inscripcion = inscripciones_map.get(pago["inscripcion_id"])
        if inscripcion:
            actividad = actividades_map.get(inscripcion["actividad_id"])
            estudiante = estudiantes_map.get(inscripcion["estudiante_id"])
            
            pago_info = {
                **pago,
                "actividad_nombre": actividad["nombre"] if actividad else "N/A",
                "estudiante_nombre": estudiante["nombre_completo"] if estudiante else "N/A",
                "curso_grado": estudiante["curso_grado"] if estudiante else "N/A"
            }
            pagos_enriquecidos.append(pago_info)
    
    total_ingresos = sum(p.get("monto", 0) for p in pagos if p["estado"] == PaymentStatus.COMPLETADO)
    ingresos_pendientes = sum(p.get("monto", 0) for p in pagos if p["estado"] == PaymentStatus.PENDIENTE)
    
    return {
        "pagos": pagos_enriquecidos,
        "resumen": {
            "total_pagos": len(pagos),
            "pagos_completados": len([p for p in pagos if p["estado"] == PaymentStatus.COMPLETADO]),
            "pagos_pendientes": len([p for p in pagos if p["estado"] == PaymentStatus.PENDIENTE]),
            "total_ingresos": total_ingresos,
            "ingresos_pendientes": ingresos_pendientes
        }
    }

# Communication System Endpoints

@api_router.get("/comunicacion/mensajes", response_model=List[Message])
async def get_messages(current_user: User = Depends(get_current_user)):
    """Obtener mensajes del colegio"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if current_user.role == UserRole.ADMIN_COLEGIO:
        query["colegio_id"] = current_user.colegio_id
    
    mensajes = await db.mensajes.find(query).sort("created_at", -1).to_list(1000)
    return [Message(**mensaje) for mensaje in mensajes]

@api_router.post("/comunicacion/mensajes", response_model=Message)
async def create_message(message_data: MessageCreate, current_user: User = Depends(get_current_user)):
    """Crear nuevo mensaje/circular/comunicado"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Preparar datos del mensaje
    message_dict = message_data.dict()
    message_dict.update({
        "id": str(uuid.uuid4()),
        "colegio_id": current_user.colegio_id,
        "autor_id": current_user.id,
        "autor_nombre": current_user.full_name,
        "estado": MessageStatus.BORRADOR,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "total_destinatarios": 0,
        "total_leidos": 0
    })
    
    # Serializar datetime objects
    if message_dict.get("fecha_programada"):
        message_dict["fecha_programada"] = message_dict["fecha_programada"].isoformat()
    message_dict["created_at"] = message_dict["created_at"].isoformat()
    message_dict["updated_at"] = message_dict["updated_at"].isoformat()
    
    await db.mensajes.insert_one(message_dict)
    return Message(**message_dict)

@api_router.put("/comunicacion/mensajes/{mensaje_id}", response_model=Message)
async def update_message(mensaje_id: str, update_data: MessageUpdate, current_user: User = Depends(get_current_user)):
    """Actualizar mensaje"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar propiedad del mensaje
    mensaje = await db.mensajes.find_one({"id": mensaje_id})
    if not mensaje:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO and mensaje["colegio_id"] != current_user.colegio_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Preparar actualizaciones
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    if update_dict.get("fecha_programada"):
        update_dict["fecha_programada"] = update_dict["fecha_programada"].isoformat()
    
    await db.mensajes.update_one({"id": mensaje_id}, {"$set": update_dict})
    
    updated_mensaje = await db.mensajes.find_one({"id": mensaje_id})
    return Message(**updated_mensaje)

@api_router.post("/comunicacion/mensajes/{mensaje_id}/enviar")
async def send_message(mensaje_id: str, current_user: User = Depends(get_current_user)):
    """Enviar mensaje a destinatarios"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Obtener mensaje
    mensaje = await db.mensajes.find_one({"id": mensaje_id})
    if not mensaje:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO and mensaje["colegio_id"] != current_user.colegio_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Obtener destinatarios
    destinatarios = []
    
    # Usuarios específicos
    if mensaje.get("usuarios_especificos"):
        usuarios_especificos = await db.users.find(
            {"id": {"$in": mensaje["usuarios_especificos"]}}
        ).to_list(1000)
        destinatarios.extend(usuarios_especificos)
    
    # Por roles
    if mensaje.get("dirigida_a"):
        usuarios_por_rol = await db.users.find({
            "role": {"$in": mensaje["dirigida_a"]},
            "colegio_id": mensaje["colegio_id"]
        }).to_list(1000)
        destinatarios.extend(usuarios_por_rol)
    
    # Eliminar duplicados
    usuarios_unicos = {}
    for usuario in destinatarios:
        usuarios_unicos[usuario["id"]] = usuario
    destinatarios_finales = list(usuarios_unicos.values())
    
    # Crear notificaciones para cada destinatario
    notificaciones = []
    for usuario in destinatarios_finales:
        notificacion = {
            "id": str(uuid.uuid4()),
            "mensaje_id": mensaje_id,
            "usuario_id": usuario["id"],
            "usuario_email": usuario["email"],
            "usuario_nombre": usuario["full_name"],
            "estado": NotificationStatus.NO_LEIDA,
            "created_at": datetime.utcnow().isoformat(),
            "confirmado": False
        }
        notificaciones.append(notificacion)
    
    if notificaciones:
        await db.notificaciones_comunicacion.insert_many(notificaciones)
    
    # Actualizar mensaje como enviado
    await db.mensajes.update_one(
        {"id": mensaje_id},
        {
            "$set": {
                "estado": MessageStatus.ENVIADO,
                "fecha_enviado": datetime.utcnow().isoformat(),
                "total_destinatarios": len(destinatarios_finales),
                "updated_at": datetime.utcnow().isoformat()
            }
        }
    )
    
    return {"message": f"Mensaje enviado a {len(destinatarios_finales)} destinatarios"}

@api_router.get("/comunicacion/notificaciones")
async def get_user_notifications(current_user: User = Depends(get_current_user)):
    """Obtener notificaciones del usuario actual"""
    notificaciones = await db.notificaciones_comunicacion.find(
        {"usuario_id": current_user.id}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    # Enriquecer con información del mensaje
    for notif in notificaciones:
        mensaje = await db.mensajes.find_one({"id": notif["mensaje_id"]})
        if mensaje:
            notif["mensaje_titulo"] = mensaje["titulo"]
            notif["mensaje_tipo"] = mensaje["tipo"]
            notif["mensaje_prioridad"] = mensaje["prioridad"]
    
    return notificaciones

@api_router.put("/comunicacion/notificaciones/{notificacion_id}/leer")
async def mark_notification_read(notificacion_id: str, read_data: NotificationRead, current_user: User = Depends(get_current_user)):
    """Marcar notificación como leída"""
    # Verificar que la notificación pertenece al usuario
    notificacion = await db.notificaciones_comunicacion.find_one({
        "id": notificacion_id,
        "usuario_id": current_user.id
    })
    
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    update_data = {
        "estado": NotificationStatus.LEIDA,
        "fecha_leido": datetime.utcnow().isoformat()
    }
    
    if read_data.confirmacion:
        update_data.update({
            "confirmado": True,
            "fecha_confirmacion": datetime.utcnow().isoformat()
        })
    
    await db.notificaciones_comunicacion.update_one(
        {"id": notificacion_id},
        {"$set": update_data}
    )
    
    # Actualizar estadísticas del mensaje
    mensaje_id = notificacion["mensaje_id"]
    total_leidos = await db.notificaciones_comunicacion.count_documents({
        "mensaje_id": mensaje_id,
        "estado": NotificationStatus.LEIDA
    })
    
    await db.mensajes.update_one(
        {"id": mensaje_id},
        {"$set": {"total_leidos": total_leidos}}
    )
    
    return {"message": "Notification marked as read"}

@api_router.delete("/comunicacion/mensajes/{mensaje_id}")
async def delete_message(mensaje_id: str, current_user: User = Depends(get_current_user)):
    """Eliminar mensaje"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar propiedad del mensaje
    mensaje = await db.mensajes.find_one({"id": mensaje_id})
    if not mensaje:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO and mensaje["colegio_id"] != current_user.colegio_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Eliminar mensaje y notificaciones relacionadas
    await db.mensajes.delete_one({"id": mensaje_id})
    await db.notificaciones_comunicacion.delete_many({"mensaje_id": mensaje_id})
    
    return {"message": "Message deleted successfully"}

@api_router.get("/comunicacion/estadisticas", response_model=CommunicationStats)
async def get_communication_stats(current_user: User = Depends(get_current_user)):
    """Obtener estadísticas de comunicación"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if current_user.role == UserRole.ADMIN_COLEGIO:
        query["colegio_id"] = current_user.colegio_id
    
    # Contar mensajes por estado
    mensajes = await db.mensajes.find(query).to_list(1000)
    
    total_mensajes = len(mensajes)
    mensajes_enviados = len([m for m in mensajes if m["estado"] == MessageStatus.ENVIADO])
    mensajes_borradores = len([m for m in mensajes if m["estado"] == MessageStatus.BORRADOR])
    mensajes_programados = len([m for m in mensajes if m["estado"] == MessageStatus.PROGRAMADO])
    
    # Contar mensajes por tipo
    mensajes_por_tipo = {}
    for mensaje in mensajes:
        tipo = mensaje["tipo"]
        mensajes_por_tipo[tipo] = mensajes_por_tipo.get(tipo, 0) + 1
    
    # Calcular tasa de lectura promedio
    tasa_lectura_promedio = 0.0
    if mensajes_enviados > 0:
        total_lecturas = sum([m.get("total_leidos", 0) for m in mensajes if m["estado"] == MessageStatus.ENVIADO])
        total_destinatarios = sum([m.get("total_destinatarios", 0) for m in mensajes if m["estado"] == MessageStatus.ENVIADO])
        if total_destinatarios > 0:
            tasa_lectura_promedio = (total_lecturas / total_destinatarios) * 100
    
    return CommunicationStats(
        total_mensajes=total_mensajes,
        mensajes_enviados=mensajes_enviados,
        mensajes_borradores=mensajes_borradores,
        mensajes_programados=mensajes_programados,
        tasa_lectura_promedio=round(tasa_lectura_promedio, 2),
        mensajes_por_tipo=mensajes_por_tipo
    )

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "Chuflay API - Sistema Completo con Admin Global v1.2 + Sistema de Comunicación"}

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