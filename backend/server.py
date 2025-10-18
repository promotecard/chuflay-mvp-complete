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

# Payment Administration Models
class PaymentAdminStats(BaseModel):
    total_pagos: int
    pagos_completados: int
    pagos_pendientes: int
    pagos_fallidos: int
    ingresos_totales: float
    ingresos_mes_actual: float
    ingresos_por_metodo: Dict[str, float]
    pagos_por_actividad: List[Dict[str, Any]]

class PaymentFilters(BaseModel):
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    estado: Optional[PaymentStatus] = None
    metodo: Optional[PaymentMethod] = None
    actividad_id: Optional[str] = None
    estudiante_id: Optional[str] = None

class BulkPaymentUpdate(BaseModel):
    payment_ids: List[str]
    nuevo_estado: PaymentStatus
    notas: Optional[str] = None

class PaymentReport(BaseModel):
    periodo: str
    total_ingresos: float
    total_pagos: int
    pagos_por_estado: Dict[str, int]
    ingresos_por_actividad: List[Dict[str, Any]]
    pagos_por_metodo: Dict[str, int]
    tendencia_mensual: List[Dict[str, Any]]

# POS & Marketplace Models
class ProductCategory(str, Enum):
    UNIFORMES = "uniformes"
    UTILES_ESCOLARES = "utiles_escolares"
    LIBROS = "libros"
    TECNOLOGIA = "tecnologia"
    ALIMENTACION = "alimentacion"
    DEPORTES = "deportes"
    ARTE = "arte"
    OTROS = "otros"

class ProductStatus(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    AGOTADO = "agotado"
    DESCONTINUADO = "descontinuado"

class OrderStatus(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    PREPARANDO = "preparando"
    LISTA = "lista"
    ENTREGADA = "entregada"
    CANCELADA = "cancelada"

class Product(BaseModel):
    nombre: str
    descripcion: str
    categoria: ProductCategory
    precio: float
    precio_descuento: Optional[float] = None
    stock: int
    stock_minimo: int = 10
    imagen_url: Optional[str] = None
    codigo_barras: Optional[str] = None
    marca: Optional[str] = None
    colegio_id: str
    proveedor: Optional[str] = None
    estado: ProductStatus = ProductStatus.ACTIVO
    especificaciones: Dict[str, Any] = {}

class ProductCreate(BaseModel):
    nombre: str
    descripcion: str
    categoria: ProductCategory
    precio: float
    precio_descuento: Optional[float] = None
    stock: int
    stock_minimo: int = 10
    imagen_url: Optional[str] = None
    codigo_barras: Optional[str] = None
    marca: Optional[str] = None
    proveedor: Optional[str] = None
    especificaciones: Dict[str, Any] = {}

class ProductUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    precio_descuento: Optional[float] = None
    stock: Optional[int] = None
    stock_minimo: Optional[int] = None
    imagen_url: Optional[str] = None
    estado: Optional[ProductStatus] = None
    especificaciones: Optional[Dict[str, Any]] = None

class CartItem(BaseModel):
    producto_id: str
    cantidad: int
    precio_unitario: float

class Order(BaseModel):
    usuario_id: str
    colegio_id: str
    items: List[CartItem]
    subtotal: float
    impuestos: float = 0.0
    descuentos: float = 0.0
    total: float
    metodo_pago: PaymentMethod
    estado: OrderStatus = OrderStatus.PENDIENTE
    notas: Optional[str] = None
    fecha_entrega: Optional[datetime] = None
    entregado_por: Optional[str] = None

class OrderCreate(BaseModel):
    items: List[CartItem]
    metodo_pago: PaymentMethod
    notas: Optional[str] = None

class MarketplaceStats(BaseModel):
    total_productos: int
    productos_activos: int
    productos_agotados: int
    valor_inventario: float
    ordenes_pendientes: int
    ventas_mes: float
    productos_mas_vendidos: List[Dict[str, Any]]

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
    
    # Convert ISO string dates back to datetime objects for Pydantic
    for mensaje in mensajes:
        if mensaje.get("created_at") and isinstance(mensaje["created_at"], str):
            mensaje["created_at"] = datetime.fromisoformat(mensaje["created_at"])
        if mensaje.get("updated_at") and isinstance(mensaje["updated_at"], str):
            mensaje["updated_at"] = datetime.fromisoformat(mensaje["updated_at"])
        if mensaje.get("fecha_programada") and isinstance(mensaje["fecha_programada"], str):
            mensaje["fecha_programada"] = datetime.fromisoformat(mensaje["fecha_programada"])
        if mensaje.get("fecha_enviado") and isinstance(mensaje["fecha_enviado"], str):
            mensaje["fecha_enviado"] = datetime.fromisoformat(mensaje["fecha_enviado"])
    
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
    
    result = await db.mensajes.update_one({"id": mensaje_id}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Message not found during update")
    
    updated_mensaje = await db.mensajes.find_one({"id": mensaje_id})
    if not updated_mensaje:
        raise HTTPException(status_code=404, detail="Message not found after update")
    
    # Convert ISO string dates back to datetime objects for Pydantic
    if updated_mensaje.get("created_at") and isinstance(updated_mensaje["created_at"], str):
        updated_mensaje["created_at"] = datetime.fromisoformat(updated_mensaje["created_at"])
    if updated_mensaje.get("updated_at") and isinstance(updated_mensaje["updated_at"], str):
        updated_mensaje["updated_at"] = datetime.fromisoformat(updated_mensaje["updated_at"])
    if updated_mensaje.get("fecha_programada") and isinstance(updated_mensaje["fecha_programada"], str):
        updated_mensaje["fecha_programada"] = datetime.fromisoformat(updated_mensaje["fecha_programada"])
    if updated_mensaje.get("fecha_enviado") and isinstance(updated_mensaje["fecha_enviado"], str):
        updated_mensaje["fecha_enviado"] = datetime.fromisoformat(updated_mensaje["fecha_enviado"])
    
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

# Additional APIs for Parent Interface

@api_router.get("/actividades/publicas")
async def get_public_activities():
    """Obtener actividades públicas para padres"""
    actividades = await db.actividades.find({"visibilidad": {"$ne": "privada"}}).to_list(1000)
    return [Activity(**actividad) for actividad in actividades if actividad]

@api_router.get("/estudiantes/mis-hijos")
async def get_mis_hijos(current_user: User = Depends(get_current_user)):
    """Obtener hijos del padre actual"""
    if current_user.role != UserRole.PADRE:
        raise HTTPException(status_code=403, detail="Only parents can access this endpoint")
    
    estudiantes = await db.estudiantes.find({"padre_id": current_user.id}).to_list(1000)
    return [Estudiante(**estudiante) for estudiante in estudiantes]

@api_router.get("/inscripciones/mis-inscripciones")
async def get_mis_inscripciones(current_user: User = Depends(get_current_user)):
    """Obtener inscripciones de los hijos del padre actual"""
    if current_user.role != UserRole.PADRE:
        raise HTTPException(status_code=403, detail="Only parents can access this endpoint")
    
    # Obtener hijos del padre
    estudiantes = await db.estudiantes.find({"padre_id": current_user.id}).to_list(1000)
    estudiantes_ids = [e["id"] for e in estudiantes]
    
    if not estudiantes_ids:
        return []
    
    # Obtener inscripciones de los hijos
    inscripciones = await db.inscripciones.find(
        {"estudiante_id": {"$in": estudiantes_ids}}
    ).to_list(1000)
    
    # Enriquecer con información de actividades y estudiantes
    actividades = await db.actividades.find().to_list(1000)
    actividades_map = {a["id"]: a for a in actividades}
    estudiantes_map = {e["id"]: e for e in estudiantes}
    
    inscripciones_enriquecidas = []
    for inscripcion in inscripciones:
        actividad = actividades_map.get(inscripcion["actividad_id"])
        estudiante = estudiantes_map.get(inscripcion["estudiante_id"])
        
        inscripcion_info = {
            **inscripcion,
            "actividad_nombre": actividad["nombre"] if actividad else "N/A",
            "estudiante_nombre": estudiante["nombre_completo"] if estudiante else "N/A"
        }
        inscripciones_enriquecidas.append(inscripcion_info)
    
    return inscripciones_enriquecidas

# Payment Administration System Endpoints

@api_router.get("/admin/pagos/estadisticas", response_model=PaymentAdminStats)
async def get_payment_admin_stats(current_user: User = Depends(get_current_user)):
    """Obtener estadísticas administrativas de pagos"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Filtrar por colegio si es admin de colegio
    query = {}
    if current_user.role == UserRole.ADMIN_COLEGIO:
        # Obtener inscripciones del colegio
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        if inscripcion_ids:
            query["inscripcion_id"] = {"$in": inscripcion_ids}
        else:
            query["inscripcion_id"] = {"$in": []}  # No results
    
    pagos = await db.pagos.find(query).to_list(1000)
    
    # Calcular estadísticas
    total_pagos = len(pagos)
    pagos_completados = len([p for p in pagos if p["estado"] == PaymentStatus.COMPLETADO])
    pagos_pendientes = len([p for p in pagos if p["estado"] == PaymentStatus.PENDIENTE])
    pagos_fallidos = len([p for p in pagos if p["estado"] == PaymentStatus.FALLIDO])
    
    ingresos_totales = sum([p.get("monto", 0) for p in pagos if p["estado"] == PaymentStatus.COMPLETADO])
    
    # Ingresos del mes actual
    mes_actual = datetime.utcnow().replace(day=1)
    ingresos_mes_actual = sum([
        p.get("monto", 0) for p in pagos 
        if p["estado"] == PaymentStatus.COMPLETADO and 
        datetime.fromisoformat(p["created_at"]) >= mes_actual
    ])
    
    # Ingresos por método de pago
    ingresos_por_metodo = {}
    for pago in pagos:
        if pago["estado"] == PaymentStatus.COMPLETADO:
            metodo = pago["metodo_pago"]
            ingresos_por_metodo[metodo] = ingresos_por_metodo.get(metodo, 0) + pago.get("monto", 0)
    
    # Pagos por actividad (necesitamos enriquecer con datos de actividad)
    pagos_por_actividad = []
    if pagos:
        # Obtener inscripciones y actividades para enriquecer
        inscripciones_dict = {}
        if current_user.role == UserRole.ADMIN_COLEGIO:
            inscripciones_data = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        else:
            inscripciones_data = await db.inscripciones.find().to_list(1000)
        
        for insc in inscripciones_data:
            inscripciones_dict[insc["id"]] = insc
        
        actividades_ids = list(set([insc.get("actividad_id") for insc in inscripciones_data if insc.get("actividad_id")]))
        actividades = await db.actividades.find({"id": {"$in": actividades_ids}}).to_list(1000)
        actividades_dict = {act["id"]: act for act in actividades}
        
        actividad_ingresos = {}
        for pago in pagos:
            if pago["estado"] == PaymentStatus.COMPLETADO:
                inscripcion = inscripciones_dict.get(pago["inscripcion_id"])
                if inscripcion:
                    actividad_id = inscripcion.get("actividad_id")
                    actividad = actividades_dict.get(actividad_id)
                    if actividad:
                        nombre_actividad = actividad["nombre"]
                        actividad_ingresos[nombre_actividad] = actividad_ingresos.get(nombre_actividad, 0) + pago.get("monto", 0)
        
        pagos_por_actividad = [{"actividad": k, "ingresos": v} for k, v in actividad_ingresos.items()]
        pagos_por_actividad.sort(key=lambda x: x["ingresos"], reverse=True)
    
    return PaymentAdminStats(
        total_pagos=total_pagos,
        pagos_completados=pagos_completados,
        pagos_pendientes=pagos_pendientes,
        pagos_fallidos=pagos_fallidos,
        ingresos_totales=ingresos_totales,
        ingresos_mes_actual=ingresos_mes_actual,
        ingresos_por_metodo=ingresos_por_metodo,
        pagos_por_actividad=pagos_por_actividad
    )

@api_router.get("/admin/pagos/listado")
async def get_admin_payments(
    filters: PaymentFilters = None,
    current_user: User = Depends(get_current_user)
):
    """Obtener listado de pagos para administración"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Base query
    query = {}
    
    # Filtrar por colegio si es admin de colegio
    if current_user.role == UserRole.ADMIN_COLEGIO:
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        if inscripcion_ids:
            query["inscripcion_id"] = {"$in": inscripcion_ids}
        else:
            return []  # No results for this college
    
    # Aplicar filtros adicionales si se proporcionan
    if filters:
        if filters.estado:
            query["estado"] = filters.estado
        if filters.metodo:
            query["metodo_pago"] = filters.metodo
        if filters.fecha_inicio or filters.fecha_fin:
            date_query = {}
            if filters.fecha_inicio:
                date_query["$gte"] = filters.fecha_inicio.isoformat()
            if filters.fecha_fin:
                date_query["$lte"] = filters.fecha_fin.isoformat()
            if date_query:
                query["created_at"] = date_query
    
    # Obtener pagos
    pagos = await db.pagos.find(query).sort("created_at", -1).to_list(1000)
    
    # Enriquecer con información de inscripciones, estudiantes y actividades
    pagos_enriquecidos = []
    if pagos:
        inscripciones = await db.inscripciones.find().to_list(1000)
        inscripciones_dict = {i["id"]: i for i in inscripciones}
        
        estudiantes = await db.estudiantes.find().to_list(1000)
        estudiantes_dict = {e["id"]: e for e in estudiantes}
        
        actividades = await db.actividades.find().to_list(1000)
        actividades_dict = {a["id"]: a for a in actividades}
        
        for pago in pagos:
            inscripcion = inscripciones_dict.get(pago["inscripcion_id"])
            if inscripcion:
                estudiante = estudiantes_dict.get(inscripcion.get("estudiante_id"))
                actividad = actividades_dict.get(inscripcion.get("actividad_id"))
                
                pago_enriquecido = {
                    **pago,
                    "estudiante_nombre": estudiante["nombre_completo"] if estudiante else "N/A",
                    "actividad_nombre": actividad["nombre"] if actividad else "N/A",
                    "curso_grado": estudiante["curso_grado"] if estudiante else "N/A"
                }
                pagos_enriquecidos.append(pago_enriquecido)
    
    return pagos_enriquecidos

@api_router.put("/admin/pagos/bulk-update")
async def bulk_update_payments(
    update_data: BulkPaymentUpdate,
    current_user: User = Depends(get_current_user)
):
    """Actualización masiva de pagos"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar que los pagos pertenezcan al colegio (si es admin de colegio)
    if current_user.role == UserRole.ADMIN_COLEGIO:
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        
        pagos_a_actualizar = await db.pagos.find({
            "id": {"$in": update_data.payment_ids},
            "inscripcion_id": {"$in": inscripcion_ids}
        }).to_list(1000)
        
        if len(pagos_a_actualizar) != len(update_data.payment_ids):
            raise HTTPException(status_code=403, detail="Some payments don't belong to your college")
    
    # Realizar actualización
    update_dict = {
        "estado": update_data.nuevo_estado,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if update_data.notas:
        update_dict["notas_admin"] = update_data.notas
    
    result = await db.pagos.update_many(
        {"id": {"$in": update_data.payment_ids}},
        {"$set": update_dict}
    )
    
    return {"message": f"Updated {result.modified_count} payments successfully"}

@api_router.get("/admin/pagos/reportes", response_model=PaymentReport)
async def get_payment_reports(
    periodo: str = "mensual",  # mensual, trimestral, anual
    current_user: User = Depends(get_current_user)
):
    """Generar reportes de pagos"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calcular fechas según período
    now = datetime.utcnow()
    if periodo == "mensual":
        fecha_inicio = now.replace(day=1)
    elif periodo == "trimestral":
        mes_inicio_trimestre = ((now.month - 1) // 3) * 3 + 1
        fecha_inicio = now.replace(month=mes_inicio_trimestre, day=1)
    else:  # anual
        fecha_inicio = now.replace(month=1, day=1)
    
    # Query base para pagos del período
    query = {
        "created_at": {"$gte": fecha_inicio.isoformat()}
    }
    
    # Filtrar por colegio si es admin de colegio
    if current_user.role == UserRole.ADMIN_COLEGIO:
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        if inscripcion_ids:
            query["inscripcion_id"] = {"$in": inscripcion_ids}
        else:
            query["inscripcion_id"] = {"$in": []}
    
    pagos = await db.pagos.find(query).to_list(1000)
    
    # Calcular métricas del reporte
    total_ingresos = sum([p.get("monto", 0) for p in pagos if p["estado"] == PaymentStatus.COMPLETADO])
    total_pagos = len(pagos)
    
    pagos_por_estado = {}
    for pago in pagos:
        estado = pago["estado"]
        pagos_por_estado[estado] = pagos_por_estado.get(estado, 0) + 1
    
    pagos_por_metodo = {}
    for pago in pagos:
        metodo = pago["metodo_pago"]
        pagos_por_metodo[metodo] = pagos_por_metodo.get(metodo, 0) + 1
    
    # Ingresos por actividad (simplificado)
    ingresos_por_actividad = []
    
    # Tendencia mensual (últimos 6 meses)
    tendencia_mensual = []
    for i in range(6):
        mes_fecha = now.replace(day=1) - timedelta(days=30*i)
        mes_siguiente = mes_fecha.replace(month=mes_fecha.month+1 if mes_fecha.month < 12 else 1, 
                                         year=mes_fecha.year if mes_fecha.month < 12 else mes_fecha.year+1)
        
        pagos_mes = [p for p in pagos 
                    if mes_fecha.isoformat() <= p["created_at"] < mes_siguiente.isoformat()]
        
        ingresos_mes = sum([p.get("monto", 0) for p in pagos_mes if p["estado"] == PaymentStatus.COMPLETADO])
        
        tendencia_mensual.append({
            "mes": mes_fecha.strftime("%Y-%m"),
            "ingresos": ingresos_mes,
            "pagos": len(pagos_mes)
        })
    
    return PaymentReport(
        periodo=periodo,
        total_ingresos=total_ingresos,
        total_pagos=total_pagos,
        pagos_por_estado=pagos_por_estado,
        ingresos_por_actividad=ingresos_por_actividad,
        pagos_por_metodo=pagos_por_metodo,
        tendencia_mensual=list(reversed(tendencia_mensual))
    )

@api_router.post("/admin/pagos/{payment_id}/manual-confirm")
async def manual_confirm_payment(
    payment_id: str,
    notas: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Confirmar pago manualmente (para pagos en efectivo/transferencia)"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar que el pago existe y pertenece al colegio
    pago = await db.pagos.find_one({"id": payment_id})
    if not pago:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO:
        inscripcion = await db.inscripciones.find_one({"id": pago["inscripcion_id"]})
        if not inscripcion or inscripcion["colegio_id"] != current_user.colegio_id:
            raise HTTPException(status_code=403, detail="Payment doesn't belong to your college")
    
    # Actualizar el pago
    update_data = {
        "estado": PaymentStatus.COMPLETADO,
        "fecha_procesamiento": datetime.utcnow().isoformat(),
        "confirmado_por": current_user.id,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if notas:
        update_data["notas_confirmacion"] = notas
    
    await db.pagos.update_one({"id": payment_id}, {"$set": update_data})
    
    # Actualizar estado de inscripción si es necesario
    await db.inscripciones.update_one(
        {"id": pago["inscripcion_id"]},
        {"$set": {"estado": InscriptionStatus.CONFIRMADA}}
    )
    
    return {"message": "Payment confirmed successfully"}

# POS & Marketplace System Endpoints

@api_router.get("/marketplace/productos", response_model=List[Product])
async def get_products(
    categoria: Optional[ProductCategory] = None,
    busqueda: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Obtener productos del marketplace"""
    query = {"colegio_id": current_user.colegio_id}
    
    if categoria:
        query["categoria"] = categoria
    
    if busqueda:
        query["$or"] = [
            {"nombre": {"$regex": busqueda, "$options": "i"}},
            {"descripcion": {"$regex": busqueda, "$options": "i"}},
            {"marca": {"$regex": busqueda, "$options": "i"}}
        ]
    
    productos = await db.productos.find(query).to_list(1000)
    return [Product(**producto) for producto in productos]

@api_router.post("/marketplace/productos", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    """Crear nuevo producto (Admin)"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    product_dict = product_data.dict()
    product_dict.update({
        "id": str(uuid.uuid4()),
        "colegio_id": current_user.colegio_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    })
    
    await db.productos.insert_one(product_dict)
    return Product(**product_dict)

@api_router.put("/marketplace/productos/{producto_id}", response_model=Product)
async def update_product(
    producto_id: str, 
    update_data: ProductUpdate, 
    current_user: User = Depends(get_current_user)
):
    """Actualizar producto"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar propiedad del producto
    producto = await db.productos.find_one({"id": producto_id})
    if not producto:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO and producto["colegio_id"] != current_user.colegio_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    await db.productos.update_one({"id": producto_id}, {"$set": update_dict})
    
    updated_producto = await db.productos.find_one({"id": producto_id})
    return Product(**updated_producto)

@api_router.delete("/marketplace/productos/{producto_id}")
async def delete_product(producto_id: str, current_user: User = Depends(get_current_user)):
    """Eliminar producto"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar propiedad del producto
    producto = await db.productos.find_one({"id": producto_id})
    if not producto:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO and producto["colegio_id"] != current_user.colegio_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.productos.delete_one({"id": producto_id})
    return {"message": "Product deleted successfully"}

@api_router.get("/marketplace/estadisticas", response_model=MarketplaceStats)
async def get_marketplace_stats(current_user: User = Depends(get_current_user)):
    """Obtener estadísticas del marketplace"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if current_user.role == UserRole.ADMIN_COLEGIO:
        query["colegio_id"] = current_user.colegio_id
    
    productos = await db.productos.find(query).to_list(1000)
    
    total_productos = len(productos)
    productos_activos = len([p for p in productos if p["estado"] == ProductStatus.ACTIVO])
    productos_agotados = len([p for p in productos if p["stock"] <= 0])
    valor_inventario = sum([p["precio"] * p["stock"] for p in productos])
    
    # Órdenes del mes actual
    mes_actual = datetime.utcnow().replace(day=1)
    ordenes_query = {"created_at": {"$gte": mes_actual.isoformat()}}
    if current_user.role == UserRole.ADMIN_COLEGIO:
        ordenes_query["colegio_id"] = current_user.colegio_id
    
    ordenes = await db.ordenes.find(ordenes_query).to_list(1000)
    ordenes_pendientes = len([o for o in ordenes if o["estado"] in [OrderStatus.PENDIENTE, OrderStatus.CONFIRMADA, OrderStatus.PREPARANDO]])
    ventas_mes = sum([o["total"] for o in ordenes if o["estado"] == OrderStatus.ENTREGADA])
    
    # Productos más vendidos (simplificado)
    productos_mas_vendidos = []
    
    return MarketplaceStats(
        total_productos=total_productos,
        productos_activos=productos_activos,
        productos_agotados=productos_agotados,
        valor_inventario=valor_inventario,
        ordenes_pendientes=ordenes_pendientes,
        ventas_mes=ventas_mes,
        productos_mas_vendidos=productos_mas_vendidos
    )

@api_router.post("/marketplace/ordenes", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: User = Depends(get_current_user)):
    """Crear nueva orden"""
    # Calcular totales
    subtotal = sum([item.precio_unitario * item.cantidad for item in order_data.items])
    impuestos = subtotal * 0.19  # 19% IVA
    total = subtotal + impuestos
    
    # Verificar stock de productos
    for item in order_data.items:
        producto = await db.productos.find_one({"id": item.producto_id})
        if not producto:
            raise HTTPException(status_code=404, detail=f"Product {item.producto_id} not found")
        
        if producto["stock"] < item.cantidad:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {producto['nombre']}. Available: {producto['stock']}, Requested: {item.cantidad}"
            )
    
    # Crear orden
    order_dict = {
        "id": str(uuid.uuid4()),
        "usuario_id": current_user.id,
        "colegio_id": current_user.colegio_id,
        "items": [item.dict() for item in order_data.items],
        "subtotal": subtotal,
        "impuestos": impuestos,
        "descuentos": 0.0,
        "total": total,
        "metodo_pago": order_data.metodo_pago,
        "estado": OrderStatus.PENDIENTE,
        "notas": order_data.notas,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    await db.ordenes.insert_one(order_dict)
    
    # Actualizar stock de productos
    for item in order_data.items:
        await db.productos.update_one(
            {"id": item.producto_id},
            {"$inc": {"stock": -item.cantidad}}
        )
    
    return Order(**order_dict)

@api_router.get("/marketplace/ordenes")
async def get_orders(current_user: User = Depends(get_current_user)):
    """Obtener órdenes del usuario o del colegio"""
    if current_user.role in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        # Admins ven todas las órdenes del colegio
        query = {}
        if current_user.role == UserRole.ADMIN_COLEGIO:
            query["colegio_id"] = current_user.colegio_id
    else:
        # Usuarios ven solo sus órdenes
        query = {"usuario_id": current_user.id}
    
    ordenes = await db.ordenes.find(query).sort("created_at", -1).to_list(1000)
    
    # Enriquecer con información de productos
    for orden in ordenes:
        for item in orden["items"]:
            producto = await db.productos.find_one({"id": item["producto_id"]})
            if producto:
                item["producto_nombre"] = producto["nombre"]
                item["producto_imagen"] = producto.get("imagen_url")
    
    return ordenes

@api_router.put("/marketplace/ordenes/{orden_id}/estado")
async def update_order_status(
    orden_id: str,
    nuevo_estado: OrderStatus,
    current_user: User = Depends(get_current_user)
):
    """Actualizar estado de orden (Solo admins)"""
    if current_user.role not in [UserRole.ADMIN_COLEGIO, UserRole.ADMIN_GLOBAL]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verificar propiedad de la orden
    orden = await db.ordenes.find_one({"id": orden_id})
    if not orden:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role == UserRole.ADMIN_COLEGIO and orden["colegio_id"] != current_user.colegio_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = {
        "estado": nuevo_estado,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if nuevo_estado == OrderStatus.ENTREGADA:
        update_data["fecha_entrega"] = datetime.utcnow().isoformat()
        update_data["entregado_por"] = current_user.full_name
    
    await db.ordenes.update_one({"id": orden_id}, {"$set": update_data})
    
    return {"message": f"Order status updated to {nuevo_estado}"}

# Create Test Users Endpoint (for development)
@api_router.post("/create-test-users")
async def create_test_users():
    """Crear usuarios de prueba para testing"""
    
    # Crear colegio de prueba primero
    test_colegio = {
        "id": "test-colegio-001",
        "nombre": "Colegio Demo",
        "direccion": "Calle Principal 123",
        "telefono": "+56912345678",
        "email": "demo@colegio.cl",
        "director": "Director Test",
        "nivel_educativo": "Mixto",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Verificar si el colegio ya existe
    existing_colegio = await db.colegios.find_one({"id": test_colegio["id"]})
    if not existing_colegio:
        await db.colegios.insert_one(test_colegio)
    
    # Usuarios de prueba
    test_users = [
        {
            "id": "admin-global-001",
            "email": "admin@chuflay.com",
            "hashed_password": hash_password("admin123"),
            "full_name": "Admin Global",
            "nombre_completo": "Admin Global",
            "role": UserRole.ADMIN_GLOBAL,
            "colegio_id": None,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "admin-colegio-001", 
            "email": "admin@demo.com",
            "hashed_password": hash_password("admin123"),
            "full_name": "Admin Colegio Demo",
            "nombre_completo": "Admin Colegio Demo",
            "role": UserRole.ADMIN_COLEGIO,
            "colegio_id": "test-colegio-001",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "padre-001",
            "email": "padre@demo.com", 
            "hashed_password": hash_password("padre123"),
            "full_name": "María González",
            "nombre_completo": "María González",
            "role": UserRole.PADRE,
            "colegio_id": "test-colegio-001",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "estudiante-001",
            "email": "estudiante@demo.com",
            "hashed_password": hash_password("estudiante123"), 
            "full_name": "Juan González",
            "nombre_completo": "Juan González",
            "role": UserRole.ESTUDIANTE,
            "colegio_id": "test-colegio-001",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "profesor-001",
            "email": "profesor@demo.com",
            "hashed_password": hash_password("profesor123"),
            "full_name": "Carlos Profesor",
            "nombre_completo": "Carlos Profesor", 
            "role": UserRole.PROFESOR,
            "colegio_id": "test-colegio-001",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        # Verificar si el usuario ya existe
        existing_user = await db.users.find_one({"email": user_data["email"]})
        if not existing_user:
            await db.users.insert_one(user_data)
            created_users.append({
                "email": user_data["email"],
                "role": user_data["role"],
                "full_name": user_data["full_name"]
            })
        else:
            # Usuario ya existe, agregar a la lista con nota
            created_users.append({
                "email": user_data["email"],
                "role": user_data["role"], 
                "full_name": user_data["full_name"],
                "status": "already_exists"
            })
    
    return {
        "message": "Test users creation completed",
        "colegio_created": test_colegio["nombre"],
        "users": created_users,
        "credentials": [
            {"role": "Admin Global", "email": "admin@chuflay.com", "password": "admin123"},
            {"role": "Admin Colegio", "email": "admin@demo.com", "password": "admin123"},
            {"role": "Padre", "email": "padre@demo.com", "password": "padre123"},
            {"role": "Estudiante", "email": "estudiante@demo.com", "password": "estudiante123"},
            {"role": "Profesor", "email": "profesor@demo.com", "password": "profesor123"}
        ]
    }

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "Chuflay API - Sistema Completo v1.6 + Test Users Ready"}

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