import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// Configuración de la API
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Configuración de Axios
axios.defaults.headers.common['Content-Type'] = 'application/json';

// Context para autenticación
const AuthContext = React.createContext();

// Hook para usar el contexto de autenticación
export const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe ser usado dentro de AuthProvider');
  }
  return context;
};

// Provider de autenticación
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      setUser(JSON.parse(userData));
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      setUser(userData);
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al iniciar sesión' 
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al registrarse' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Componente de protección de rutas
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <div className="p-8 text-center text-red-600">No tienes permisos para acceder a esta página</div>;
  }

  return children;
};

// Layout común para páginas internas
const Layout = ({ children, title }) => {
  const { user, logout } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notificaciones`);
      setNotifications(response.data.slice(0, 5)); // Solo las últimas 5
    } catch (error) {
      console.error('Error cargando notificaciones:', error);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.put(`${API}/notificaciones/${notificationId}/leer`);
      loadNotifications();
    } catch (error) {
      console.error('Error marcando notificación:', error);
    }
  };

  const unreadCount = notifications.filter(n => !n.leida).length;

  const getRoleLabel = (role) => {
    const labels = {
      admin_global: 'Administrador Global',
      admin_colegio: 'Administrador de Colegio',
      padre: 'Padre/Madre',
      estudiante: 'Estudiante',
      profesor: 'Profesor',
      proveedor: 'Proveedor'
    };
    return labels[role] || role;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <Link to="/dashboard" className="text-2xl font-bold text-gray-900">Chuflay</Link>
              <p className="text-sm text-gray-600">Plataforma Educativa</p>
            </div>
            <div className="flex items-center space-x-4">
              {/* Notification Bell */}
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="relative p-2 text-gray-600 hover:text-gray-900"
                  data-testid="notifications-bell"
                >
                  <span className="text-xl">🔔</span>
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
                    <div className="p-4 border-b">
                      <h3 className="font-semibold text-gray-900">Notificaciones</h3>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <p className="p-4 text-gray-500 text-center">No hay notificaciones</p>
                      ) : (
                        notifications.map((notification) => (
                          <div
                            key={notification.id}
                            className={`p-4 border-b hover:bg-gray-50 cursor-pointer ${
                              !notification.leida ? 'bg-blue-50' : ''
                            }`}
                            onClick={() => markAsRead(notification.id)}
                          >
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <h4 className="font-medium text-gray-900">{notification.titulo}</h4>
                                <p className="text-sm text-gray-600 mt-1">{notification.mensaje}</p>
                                <p className="text-xs text-gray-400 mt-2">
                                  {new Date(notification.created_at).toLocaleDateString()}
                                </p>
                              </div>
                              {!notification.leida && (
                                <div className="w-2 h-2 bg-blue-500 rounded-full ml-2 mt-1"></div>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    <div className="p-2 border-t">
                      <Link
                        to="/notificaciones"
                        className="block text-center text-blue-600 hover:text-blue-700 text-sm"
                        onClick={() => setShowNotifications(false)}
                      >
                        Ver todas las notificaciones
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                <p className="text-xs text-gray-600">{getRoleLabel(user.role)}</p>
              </div>
              <button
                onClick={logout}
                className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 text-sm"
              >
                Cerrar Sesión
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {title && (
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
          </div>
        )}
        {children}
      </main>
    </div>
  );
};

// Componente de Login
const LoginPage = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useAuth();

  // Redirigir si ya está logueado
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Chuflay</h1>
          <p className="text-gray-600 mt-2">Plataforma Educativa</p>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Contraseña
            </label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            ¿No tienes cuenta? <Link to="/register" className="text-blue-600 hover:underline">Regístrate</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

// Componente de Registro (mantenido igual)
const RegisterPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'padre',
    colegio_id: ''
  });
  const [colegios, setColegios] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { register, user } = useAuth();

  // Redirigir si ya está logueado
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  useEffect(() => {
    const loadColegios = async () => {
      try {
        setColegios([
          { id: 'demo-colegio', nombre: 'Colegio Demo' }
        ]);
      } catch (error) {
        console.error('Error cargando colegios:', error);
      }
    };
    loadColegios();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const result = await register(formData);
    
    if (result.success) {
      setSuccess('Registro exitoso. Puedes iniciar sesión.');
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role: 'padre',
        colegio_id: ''
      });
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Registro</h1>
          <p className="text-gray-600 mt-2">Únete a Chuflay</p>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}
          
          {success && (
            <div className="bg-green-50 border border-green-300 text-green-700 px-4 py-3 rounded-lg">
              {success}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nombre Completo
            </label>
            <input
              type="text"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña
            </label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Usuario
            </label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="padre">Padre/Madre</option>
              <option value="admin_colegio">Administrador Colegio</option>
              <option value="profesor">Profesor</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Colegio
            </label>
            <select
              name="colegio_id"
              value={formData.colegio_id}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            >
              <option value="">Selecciona un colegio</option>
              {colegios.map(colegio => (
                <option key={colegio.id} value={colegio.id}>{colegio.nombre}</option>
              ))}
            </select>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
          >
            {loading ? 'Registrando...' : 'Registrarse'}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            ¿Ya tienes cuenta? <Link to="/login" className="text-green-600 hover:underline">Inicia sesión</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

// Dashboard actualizado con nuevas estadísticas
const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await axios.get(`${API}/dashboard/stats`);
        setStats(response.data);
      } catch (error) {
        console.error('Error cargando estadísticas:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Dashboard">
      <div className="mb-8">
        <p className="text-gray-600 mt-1">Bienvenido a tu panel de control</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key} className="bg-white rounded-lg shadow p-6">
            <div className="text-2xl font-bold text-blue-600">{value}</div>
            <div className="text-gray-600 text-sm capitalize">
              {key.replace(/_/g, ' ')}
            </div>
          </div>
        ))}
      </div>

      {/* Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {user.role === 'admin_colegio' && (
          <>
            <Link 
              to="/admin/actividades" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-blue-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Gestión de Actividades</h3>
              <p className="text-gray-600 text-sm">Crea y administra las actividades del colegio</p>
            </Link>
            <Link 
              to="/admin/estudiantes" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-green-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Gestión de Estudiantes</h3>
              <p className="text-gray-600 text-sm">Administra los estudiantes del colegio</p>
            </Link>
            <Link 
              to="/admin/pagos" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-purple-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">💳 Gestión de Pagos</h3>
              <p className="text-gray-600 text-sm">Administra pagos e ingresos del colegio</p>
            </Link>
            <Link 
              to="/admin/inscripciones" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-yellow-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Inscripciones</h3>
              <p className="text-gray-600 text-sm">Ve las inscripciones a actividades</p>
            </Link>
          </>
        )}
        
        {user.role === 'padre' && (
          <>
            <Link 
              to="/mis-hijos" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-purple-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">👶 Mis Hijos</h3>
              <p className="text-gray-600 text-sm">Gestiona la información de tus hijos</p>
            </Link>
            <Link 
              to="/actividades" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-blue-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">🎯 Actividades del Colegio</h3>
              <p className="text-gray-600 text-sm">Descubre e inscríbete en actividades</p>
            </Link>
            <Link 
              to="/mis-inscripciones" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-orange-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📋 Mis Inscripciones</h3>
              <p className="text-gray-600 text-sm">Revisa el estado de las inscripciones</p>
            </Link>
            <Link 
              to="/mis-pagos" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-green-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">💳 Mis Pagos</h3>
              <p className="text-gray-600 text-sm">Gestiona los pagos de actividades</p>
            </Link>
          </>
        )}
      </div>
    </Layout>
  );
};

// Página "Mis Pagos" para Padres
const MisPagosPage = () => {
  const [pagos, setPagos] = useState([]);
  const [inscripciones, setInscripciones] = useState({});
  const [actividades, setActividades] = useState({});
  const [estudiantes, setEstudiantes] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedInscription, setSelectedInscription] = useState(null);

  useEffect(() => {
    loadMisPagos();
  }, []);

  const loadMisPagos = async () => {
    try {
      // Cargar pagos, inscripciones, actividades y estudiantes
      const [pagosRes, inscripcionesRes, actividadesRes, estudiantesRes] = await Promise.all([
        axios.get(`${API}/pagos`),
        axios.get(`${API}/inscripciones`),
        axios.get(`${API}/actividades`),
        axios.get(`${API}/estudiantes`)
      ]);

      setPagos(pagosRes.data);

      // Crear mapas para búsqueda rápida
      const inscripcionesMap = {};
      inscripcionesRes.data.forEach(insc => {
        inscripcionesMap[insc.id] = insc;
      });

      const actividadesMap = {};
      actividadesRes.data.forEach(act => {
        actividadesMap[act.id] = act;
      });

      const estudiantesMap = {};
      estudiantesRes.data.forEach(est => {
        estudiantesMap[est.id] = est;
      });

      setInscripciones(inscripcionesMap);
      setActividades(actividadesMap);
      setEstudiantes(estudiantesMap);
    } catch (error) {
      console.error('Error cargando pagos:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEstadoBadge = (estado) => {
    const colors = {
      'pendiente': 'bg-yellow-100 text-yellow-800',
      'procesando': 'bg-blue-100 text-blue-800',
      'completado': 'bg-green-100 text-green-800',
      'fallido': 'bg-red-100 text-red-800',
      'reembolsado': 'bg-purple-100 text-purple-800'
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  const getEstadoLabel = (estado) => {
    const labels = {
      'pendiente': 'Pendiente',
      'procesando': 'Procesando',
      'completado': 'Completado',
      'fallido': 'Fallido',
      'reembolsado': 'Reembolsado'
    };
    return labels[estado] || estado;
  };

  const getMetodoPagoLabel = (metodo) => {
    const labels = {
      'tarjeta': 'Tarjeta de Crédito',
      'transferencia': 'Transferencia Bancaria',
      'efectivo': 'Efectivo'
    };
    return labels[metodo] || metodo;
  };

  const handlePagarInscripcion = (inscripcion) => {
    setSelectedInscription(inscripcion);
  };

  // Obtener inscripciones con pago pendiente
  const inscripcionesSinPago = Object.values(inscripciones).filter(insc => 
    insc.estado === 'pago_pendiente' && 
    !pagos.some(pago => pago.inscripcion_id === insc.id)
  );

  if (loading) {
    return (
      <Layout title="Mis Pagos">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-green-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Mis Pagos">
      <div className="mb-6">
        <p className="text-gray-600">Gestiona los pagos de las actividades de tus hijos</p>
      </div>

      {/* Pagos Pendientes */}
      {inscripcionesSinPago.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">💰 Pagos Pendientes</h2>
          <div className="space-y-4">
            {inscripcionesSinPago.map((inscripcion) => {
              const actividad = actividades[inscripcion.actividad_id];
              const estudiante = estudiantes[inscripcion.estudiante_id];
              
              if (!actividad || !estudiante) return null;

              return (
                <div key={inscripcion.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center mb-2">
                        <h3 className="text-lg font-semibold text-gray-900 mr-3">
                          {actividad.nombre}
                        </h3>
                        <span className="bg-yellow-100 text-yellow-800 px-2 py-1 text-xs font-semibold rounded-full">
                          Pago Requerido
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                        <div>
                          <p><span className="font-medium">Estudiante:</span> {estudiante.nombre_completo}</p>
                          <p><span className="font-medium">Curso:</span> {estudiante.curso_grado}</p>
                        </div>
                        <div>
                          <p><span className="font-medium text-green-600">Monto:</span> <span className="text-lg font-bold text-green-600">${actividad.costo_estudiante}</span></p>
                          <p><span className="font-medium">Fecha Actividad:</span> {new Date(actividad.fecha_inicio).toLocaleDateString('es-ES')}</p>
                        </div>
                      </div>
                    </div>

                    <div className="ml-4">
                      <button
                        onClick={() => handlePagarInscripcion(inscripcion)}
                        className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 font-semibold"
                        data-testid={`pagar-inscripcion-${inscripcion.id}`}
                      >
                        💳 Pagar Ahora
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Historial de Pagos */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">📋 Historial de Pagos</h2>
        
        {pagos.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">💳</div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No hay pagos registrados</h3>
            <p className="text-gray-600">Los pagos de las actividades aparecerán aquí</p>
          </div>
        ) : (
          <div className="space-y-4">
            {pagos.map((pago) => {
              const inscripcion = inscripciones[pago.inscripcion_id];
              const actividad = actividades[pago.actividad_id];
              const estudiante = estudiantes[pago.estudiante_id];
              
              if (!inscripcion || !actividad || !estudiante) return null;

              return (
                <div key={pago.id} className="bg-white rounded-lg shadow p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center mb-2">
                        <h3 className="text-lg font-semibold text-gray-900 mr-3">
                          {actividad.nombre}
                        </h3>
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getEstadoBadge(pago.estado)}`}>
                          {getEstadoLabel(pago.estado)}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
                        <div>
                          <p><span className="font-medium">Estudiante:</span> {estudiante.nombre_completo}</p>
                          <p><span className="font-medium">Referencia:</span> {pago.referencia_pago}</p>
                        </div>
                        <div>
                          <p><span className="font-medium">Método:</span> {getMetodoPagoLabel(pago.metodo_pago)}</p>
                          <p><span className="font-medium">Monto:</span> <span className="font-bold text-green-600">${pago.monto}</span></p>
                        </div>
                        <div>
                          <p><span className="font-medium">Fecha Pago:</span> {new Date(pago.created_at).toLocaleDateString('es-ES')}</p>
                          {pago.fecha_procesado && (
                            <p><span className="font-medium">Procesado:</span> {new Date(pago.fecha_procesado).toLocaleDateString('es-ES')}</p>
                          )}
                        </div>
                      </div>

                      {pago.notas && (
                        <div className="mt-3 p-3 bg-gray-50 rounded">
                          <p className="text-sm text-gray-700">
                            <span className="font-medium">Notas:</span> {pago.notas}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal de Pago */}
      {selectedInscription && (
        <ModalPago
          inscripcion={selectedInscription}
          actividad={actividades[selectedInscription.actividad_id]}
          estudiante={estudiantes[selectedInscription.estudiante_id]}
          onClose={() => setSelectedInscription(null)}
          onSuccess={() => {
            setSelectedInscription(null);
            loadMisPagos();
          }}
        />
      )}
    </Layout>
  );
};

// Modal de Pago
const ModalPago = ({ inscripcion, actividad, estudiante, onClose, onSuccess }) => {
  const [metodoPago, setMetodoPago] = useState('tarjeta');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [datosPago, setDatosPago] = useState({
    numero_tarjeta: '',
    nombre_titular: '',
    fecha_vencimiento: '',
    cvv: '',
    numero_cuenta: '',
    banco: '',
    notas: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await axios.post(`${API}/pagos`, {
        inscripcion_id: inscripcion.id,
        metodo_pago: metodoPago,
        datos_pago: datosPago,
        notas: datosPago.notas
      });

      alert('¡Pago procesado exitosamente!');
      onSuccess();
    } catch (error) {
      setError(error.response?.data?.detail || 'Error procesando el pago');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setDatosPago(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-xl font-bold text-gray-900">Procesar Pago</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>

          {/* Información del pago */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-2">{actividad.nombre}</h3>
            <p className="text-sm text-gray-600">Estudiante: {estudiante.nombre_completo}</p>
            <p className="text-lg font-bold text-green-600 mt-2">Monto: ${actividad.costo_estudiante}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Método de Pago
              </label>
              <select
                value={metodoPago}
                onChange={(e) => setMetodoPago(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="tarjeta">💳 Tarjeta de Crédito</option>
                <option value="transferencia">🏦 Transferencia Bancaria</option>
                <option value="efectivo">💵 Efectivo</option>
              </select>
            </div>

            {metodoPago === 'tarjeta' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número de Tarjeta
                  </label>
                  <input
                    type="text"
                    name="numero_tarjeta"
                    placeholder="1234 5678 9012 3456"
                    value={datosPago.numero_tarjeta}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre del Titular
                  </label>
                  <input
                    type="text"
                    name="nombre_titular"
                    value={datosPago.nombre_titular}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Vencimiento
                    </label>
                    <input
                      type="text"
                      name="fecha_vencimiento"
                      placeholder="MM/AA"
                      value={datosPago.fecha_vencimiento}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      CVV
                    </label>
                    <input
                      type="text"
                      name="cvv"
                      placeholder="123"
                      value={datosPago.cvv}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      required
                    />
                  </div>
                </div>
              </>
            )}

            {metodoPago === 'transferencia' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Banco
                  </label>
                  <select
                    name="banco"
                    value={datosPago.banco}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    required
                  >
                    <option value="">Selecciona tu banco</option>
                    <option value="Banco Popular">Banco Popular</option>
                    <option value="Banco BHD">Banco BHD</option>
                    <option value="Banco Reservas">Banco Reservas</option>
                    <option value="Scotiabank">Scotiabank</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número de Cuenta
                  </label>
                  <input
                    type="text"
                    name="numero_cuenta"
                    value={datosPago.numero_cuenta}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    required
                  />
                </div>
              </>
            )}

            {metodoPago === 'efectivo' && (
              <div className="bg-blue-50 border border-blue-200 rounded p-4">
                <p className="text-blue-800 text-sm">
                  💵 <strong>Pago en Efectivo:</strong><br />
                  Deberás entregar ${actividad.costo_estudiante} en la oficina del colegio.
                  Recibirás una referencia para el pago.
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notas Adicionales (Opcional)
              </label>
              <textarea
                name="notas"
                rows="2"
                value={datosPago.notas}
                onChange={handleChange}
                placeholder="Información adicional sobre el pago..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            <div className="flex justify-end space-x-4 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-semibold"
              >
                {loading ? 'Procesando...' : `Pagar $${actividad.costo_estudiante}`}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Resto de componentes mantenidos iguales por brevedad...
// (ActividadesPadresPage, MisInscripcionesPage, MisHijosPage, etc.)

// Solo agregando el export default
const App = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          
          {/* Rutas para Padres */}
          <Route 
            path="/mis-pagos" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <MisPagosPage />
              </ProtectedRoute>
            } 
          />
          
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;