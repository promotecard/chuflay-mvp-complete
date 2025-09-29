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

class PaymentStatus(str, Enum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    REEMBOLSADO = "reembolsado"

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
    colegio_id: Optional[str] = None
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
    datos_pago: Optional[Dict[str, Any]] = None  # Para guardar detalles específicos del método
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
    tipo: str = "general"  # general, pago, actividad, inscripcion
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
    
    # Convert date to string for MongoDB
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
    
    # Convert date strings back to date objects
    result = []
    for estudiante in estudiantes:
        if isinstance(estudiante['fecha_nacimiento'], str):
            estudiante['fecha_nacimiento'] = datetime.fromisoformat(estudiante['fecha_nacimiento']).date()
        result.append(Estudiante(**estudiante))
    
    return result

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
    
    # Crear notificación para el padre
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

# Payment endpoints
@api_router.post("/pagos", response_model=Payment)
async def create_payment(payment_data: PaymentCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PADRE:
        raise HTTPException(status_code=403, detail="Only parents can make payments")
    
    # Verificar que la inscripción existe y pertenece al padre
    inscription = await db.inscripciones.find_one({
        "id": payment_data.inscripcion_id,
        "padre_id": current_user.id
    })
    if not inscription:
        raise HTTPException(status_code=404, detail="Inscription not found")
    
    # Obtener información de la actividad
    activity = await db.actividades.find_one({"id": inscription["actividad_id"]})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Verificar que el pago no existe ya
    existing_payment = await db.pagos.find_one({"inscripcion_id": payment_data.inscripcion_id})
    if existing_payment:
        raise HTTPException(status_code=400, detail="Payment already exists for this inscription")
    
    # Crear el pago
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
    
    # Simular procesamiento según el método de pago
    if payment_data.metodo_pago == PaymentMethod.EFECTIVO:
        # Efectivo queda pendiente hasta confirmación del admin
        payment.estado = PaymentStatus.PENDIENTE
        await db.pagos.update_one({"id": payment.id}, {"$set": {"estado": PaymentStatus.PENDIENTE}})
        
        notification_msg = f"Pago en efectivo registrado. Entrega ${activity['costo_estudiante']} en el colegio con referencia {payment.referencia_pago}"
        
    elif payment_data.metodo_pago == PaymentMethod.TRANSFERENCIA:
        # Transferencia queda pendiente hasta validación
        payment.estado = PaymentStatus.PENDIENTE
        await db.pagos.update_one({"id": payment.id}, {"$set": {"estado": PaymentStatus.PENDIENTE}})
        
        notification_msg = f"Pago por transferencia registrado. Envía ${activity['costo_estudiante']} con referencia {payment.referencia_pago}"
        
    else:  # TARJETA
        # Simular pago exitoso inmediato con tarjeta
        payment.estado = PaymentStatus.COMPLETADO
        payment.fecha_procesado = datetime.utcnow()
        await db.pagos.update_one({"id": payment.id}, {"$set": {
            "estado": PaymentStatus.COMPLETADO,
            "fecha_procesado": datetime.utcnow()
        }})
        
        # Actualizar inscripción como confirmada
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
    
    # Crear notificación para el padre
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
        # Admin ve todos los pagos del colegio
        inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
        inscripcion_ids = [i["id"] for i in inscripciones]
        filter_query["inscripcion_id"] = {"$in": inscripcion_ids}
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    payments = await db.pagos.find(filter_query).to_list(1000)
    return [Payment(**payment) for payment in payments]

@api_router.put("/pagos/{payment_id}/confirmar")
async def confirm_payment(payment_id: str, current_user: User = Depends(get_current_user)):
    """Confirmar pago (solo para administradores)"""
    if current_user.role != UserRole.ADMIN_COLEGIO:
        raise HTTPException(status_code=403, detail="Only administrators can confirm payments")
    
    payment = await db.pagos.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Verificar que el pago pertenece a una inscripción del colegio del admin
    inscription = await db.inscripciones.find_one({
        "id": payment["inscripcion_id"],
        "colegio_id": current_user.colegio_id
    })
    if not inscription:
        raise HTTPException(status_code=403, detail="Payment not found in your college")
    
    # Actualizar estado del pago
    await db.pagos.update_one(
        {"id": payment_id},
        {"$set": {
            "estado": PaymentStatus.COMPLETADO,
            "fecha_procesado": datetime.utcnow()
        }}
    )
    
    # Actualizar inscripción como confirmada
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
    
    # Notificar al padre
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

# Notification endpoints
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

# Dashboard endpoints
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN_COLEGIO:
        # Estadísticas para administrador
        total_pagos = await db.pagos.count_documents({})
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
        
        # Calcular ingresos totales
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
    """Reporte de pagos para administradores"""
    if current_user.role != UserRole.ADMIN_COLEGIO:
        raise HTTPException(status_code=403, detail="Only administrators can access reports")
    
    # Obtener inscripciones del colegio
    inscripciones = await db.inscripciones.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    inscripcion_ids = [i["id"] for i in inscripciones]
    
    # Obtener pagos
    pagos = await db.pagos.find({"inscripcion_id": {"$in": inscripcion_ids}}).to_list(1000)
    
    # Obtener actividades y estudiantes para enriquecer los datos
    actividades = await db.actividades.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    estudiantes = await db.estudiantes.find({"colegio_id": current_user.colegio_id}).to_list(1000)
    
    # Crear mapas para búsqueda rápida
    actividades_map = {a["id"]: a for a in actividades}
    estudiantes_map = {e["id"]: e for e in estudiantes}
    inscripciones_map = {i["id"]: i for i in inscripciones}
    
    # Enriquecer datos de pagos
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
    
    # Estadísticas resumidas
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

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "Chuflay API - Sistema Completo v1.0"}

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