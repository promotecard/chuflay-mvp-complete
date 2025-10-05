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

// Componente de Registro
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

// Dashboard actualizado con nuevas estadísticas y navegación por roles
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
        {user.role === 'admin_global' && (
          <>
            <Link 
              to="/global/colegios" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-purple-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">🏫 Gestión de Colegios</h3>
              <p className="text-gray-600 text-sm">Administra todos los colegios de la plataforma</p>
            </Link>
            <Link 
              to="/global/reportes" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-indigo-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📊 Reportes Globales</h3>
              <p className="text-gray-600 text-sm">Analytics y métricas de toda la plataforma</p>
            </Link>
            <Link 
              to="/global/suscripciones" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-green-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">💎 Suscripciones</h3>
              <p className="text-gray-600 text-sm">Gestiona planes y facturación de colegios</p>
            </Link>
            <Link 
              to="/global/usuarios" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-red-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">👥 Gestión de Usuarios</h3>
              <p className="text-gray-600 text-sm">Administra usuarios de todos los colegios</p>
            </Link>
          </>
        )}

        {user.role === 'admin_colegio' && (
          <>
            <Link 
              to="/admin/actividades" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-blue-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">🎯 Gestión de Actividades</h3>
              <p className="text-gray-600 text-sm">Crea y administra las actividades del colegio</p>
            </Link>
            <Link 
              to="/admin/estudiantes" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-green-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">👥 Gestión de Estudiantes</h3>
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
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📋 Inscripciones</h3>
              <p className="text-gray-600 text-sm">Ve las inscripciones a actividades</p>
            </Link>
            <Link 
              to="/admin/reportes" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-indigo-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📈 Reportes</h3>
              <p className="text-gray-600 text-sm">Reportes y estadísticas del colegio</p>
            </Link>
            <Link 
              to="/admin/comunicacion" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-pink-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📢 Comunicación</h3>
              <p className="text-gray-600 text-sm">Circulares y comunicados</p>
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
            <Link 
              to="/comunicados" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-pink-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📢 Comunicados</h3>
              <p className="text-gray-600 text-sm">Lee circulares y comunicados del colegio</p>
            </Link>
            <Link 
              to="/calendario" 
              className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 border-l-4 border-yellow-500"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">📅 Calendario</h3>
              <p className="text-gray-600 text-sm">Ve el calendario escolar y eventos</p>
            </Link>
          </>
        )}
      </div>
    </Layout>
  );
};

// Página "Mis Pagos" para Padres - COMPLETA
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

// Modal de Pago - COMPLETO
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
                data-testid="confirmar-pago-btn"
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

// Componente para gestión de colegios (Global Admin)
const GlobalColegios = () => {
  const [colegios, setColegios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingColegio, setEditingColegio] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    direccion: '',
    telefono: '',
    email: '',
    director: '',
    nivel_educativo: ''
  });

  useEffect(() => {
    fetchColegios();
  }, []);

  const fetchColegios = async () => {
    try {
      const response = await axios.get(`${API}/global/colegios`);
      setColegios(response.data);
    } catch (error) {
      console.error('Error fetching colegios:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingColegio) {
        await axios.put(`${API}/global/colegios/${editingColegio.id}`, formData);
      } else {
        await axios.post(`${API}/global/colegios`, formData);
      }
      setShowModal(false);
      setEditingColegio(null);
      setFormData({
        nombre: '',
        direccion: '',
        telefono: '',
        email: '',
        director: '',
        nivel_educativo: ''
      });
      fetchColegios();
    } catch (error) {
      console.error('Error saving colegio:', error);
    }
  };

  const handleEdit = (colegio) => {
    setEditingColegio(colegio);
    setFormData({
      nombre: colegio.nombre,
      direccion: colegio.direccion,
      telefono: colegio.telefono,
      email: colegio.email,
      director: colegio.director,
      nivel_educativo: colegio.nivel_educativo
    });
    setShowModal(true);
  };

  const handleDelete = async (colegioId) => {
    if (window.confirm('¿Está seguro de eliminar este colegio?')) {
      try {
        await axios.delete(`${API}/global/colegios/${colegioId}`);
        fetchColegios();
      } catch (error) {
        console.error('Error deleting colegio:', error);
      }
    }
  };

  if (loading) {
    return (
      <Layout title="Gestión de Colegios">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Gestión de Colegios">
      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Administra todos los colegios de la plataforma</p>
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + Nuevo Colegio
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Colegio
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Director
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contacto
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nivel
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {colegios.map((colegio) => (
              <tr key={colegio.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{colegio.nombre}</div>
                    <div className="text-sm text-gray-500">{colegio.direccion}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {colegio.director}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{colegio.email}</div>
                  <div className="text-sm text-gray-500">{colegio.telefono}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {colegio.nivel_educativo}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(colegio)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDelete(colegio.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal para crear/editar colegio */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {editingColegio ? 'Editar Colegio' : 'Nuevo Colegio'}
              </h3>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nombre del Colegio
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.nombre}
                    onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Dirección
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.direccion}
                    onChange={(e) => setFormData({...formData, direccion: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Teléfono
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.telefono}
                    onChange={(e) => setFormData({...formData, telefono: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Director
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.director}
                    onChange={(e) => setFormData({...formData, director: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nivel Educativo
                  </label>
                  <select
                    required
                    value={formData.nivel_educativo}
                    onChange={(e) => setFormData({...formData, nivel_educativo: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccionar nivel</option>
                    <option value="Inicial">Inicial</option>
                    <option value="Primaria">Primaria</option>
                    <option value="Secundaria">Secundaria</option>
                    <option value="Mixto">Mixto</option>
                  </select>
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingColegio(null);
                      setFormData({
                        nombre: '',
                        direccion: '',
                        telefono: '',
                        email: '',
                        director: '',
                        nivel_educativo: ''
                      });
                    }}
                    className="px-4 py-2 text-gray-600 bg-gray-200 rounded hover:bg-gray-300"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    {editingColegio ? 'Actualizar' : 'Crear'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

// Componente para gestión de usuarios globales
const GlobalUsuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [impersonateLoading, setImpersonateLoading] = useState({});

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const fetchUsuarios = async () => {
    try {
      const response = await axios.get(`${API}/global/usuarios`);
      setUsuarios(response.data);
    } catch (error) {
      console.error('Error fetching usuarios:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleImpersonate = async (userId) => {
    setImpersonateLoading(prev => ({ ...prev, [userId]: true }));
    try {
      const response = await axios.post(`${API}/global/impersonate`, { user_id: userId });
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Reload to apply new user context
      window.location.reload();
    } catch (error) {
      console.error('Error impersonating user:', error);
      alert('Error al impersonar usuario');
    } finally {
      setImpersonateLoading(prev => ({ ...prev, [userId]: false }));
    }
  };

  const getRoleDisplayName = (role) => {
    const roleNames = {
      admin_global: 'Admin Global',
      admin_colegio: 'Admin Colegio',
      padre: 'Padre',
      estudiante: 'Estudiante',
      profesor: 'Profesor',
      proveedor: 'Proveedor'
    };
    return roleNames[role] || role;
  };

  const getRoleBadgeColor = (role) => {
    const colors = {
      admin_global: 'bg-purple-100 text-purple-800',
      admin_colegio: 'bg-blue-100 text-blue-800',
      padre: 'bg-green-100 text-green-800',
      estudiante: 'bg-yellow-100 text-yellow-800',
      profesor: 'bg-indigo-100 text-indigo-800',
      proveedor: 'bg-gray-100 text-gray-800'
    };
    return colors[role] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout title="Gestión de Usuarios">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Gestión de Usuarios">
      <div className="mb-6">
        <p className="text-gray-600">Administra usuarios de todos los colegios</p>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Usuario
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rol
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Colegio
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {usuarios.map((usuario) => (
              <tr key={usuario.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{usuario.nombre_completo}</div>
                    <div className="text-sm text-gray-500">{usuario.email}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleBadgeColor(usuario.role)}`}>
                    {getRoleDisplayName(usuario.role)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {usuario.colegio_nombre || 'N/A'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                    Activo
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {usuario.role !== 'admin_global' && (
                    <button
                      onClick={() => handleImpersonate(usuario.id)}
                      disabled={impersonateLoading[usuario.id]}
                      className="text-blue-600 hover:text-blue-900 disabled:opacity-50"
                    >
                      {impersonateLoading[usuario.id] ? 'Cargando...' : 'Impersonar'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
};

// Componente para reportes globales
const GlobalReportes = () => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGlobalStats();
  }, []);

  const fetchGlobalStats = async () => {
    try {
      const response = await axios.get(`${API}/global/estadisticas`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching global stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout title="Reportes Globales">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Reportes Globales">
      <div className="mb-6">
        <p className="text-gray-600">Analytics y métricas de toda la plataforma</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">🏫</span>
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900">{stats.total_colegios || 0}</div>
              <div className="text-sm text-gray-600">Colegios Registrados</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">👥</span>
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900">{stats.total_usuarios || 0}</div>
              <div className="text-sm text-gray-600">Usuarios Totales</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">🎯</span>
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900">{stats.total_actividades || 0}</div>
              <div className="text-sm text-gray-600">Actividades Creadas</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">📋</span>
              </div>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-gray-900">{stats.total_inscripciones || 0}</div>
              <div className="text-sm text-gray-600">Inscripciones</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Distribución por Roles</h3>
          <div className="space-y-3">
            {stats.usuarios_por_rol && Object.entries(stats.usuarios_por_rol).map(([role, count]) => (
              <div key={role} className="flex justify-between items-center">
                <span className="text-sm text-gray-600 capitalize">{role.replace(/_/g, ' ')}</span>
                <span className="text-sm font-semibold text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Ingresos Totales</h3>
          <div className="text-3xl font-bold text-green-600 mb-2">
            ${stats.ingresos_totales || 0}
          </div>
          <div className="text-sm text-gray-600">
            Ingresos Pendientes: ${stats.ingresos_pendientes || 0}
          </div>
        </div>
      </div>
    </Layout>
  );
};

// Componente para gestión de suscripciones
const GlobalSuscripciones = () => {
  const [suscripciones, setSuscripciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    colegio_id: '',
    plan: 'basico',
    precio: 0,
    vigencia_hasta: ''
  });

  useEffect(() => {
    fetchSuscripciones();
  }, []);

  const fetchSuscripciones = async () => {
    try {
      const response = await axios.get(`${API}/global/suscripciones`);
      setSuscripciones(response.data);
    } catch (error) {
      console.error('Error fetching suscripciones:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/global/suscripciones`, formData);
      setShowModal(false);
      setFormData({
        colegio_id: '',
        plan: 'basico',
        precio: 0,
        vigencia_hasta: ''
      });
      fetchSuscripciones();
    } catch (error) {
      console.error('Error creating suscripcion:', error);
    }
  };

  if (loading) {
    return (
      <Layout title="Suscripciones">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Suscripciones">
      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Gestiona planes y facturación de colegios</p>
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + Nueva Suscripción
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Colegio
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Plan
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Precio
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Vigencia
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {suscripciones.map((suscripcion) => (
              <tr key={suscripcion.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {suscripcion.colegio_nombre}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                    {suscripcion.plan}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${suscripcion.precio}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    suscripcion.estado === 'activa' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {suscripcion.estado}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(suscripcion.vigencia_hasta).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal para crear suscripción */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Nueva Suscripción</h3>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    ID del Colegio
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.colegio_id}
                    onChange={(e) => setFormData({...formData, colegio_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Plan
                  </label>
                  <select
                    value={formData.plan}
                    onChange={(e) => setFormData({...formData, plan: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="basico">Básico</option>
                    <option value="premium">Premium</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Precio
                  </label>
                  <input
                    type="number"
                    required
                    value={formData.precio}
                    onChange={(e) => setFormData({...formData, precio: Number(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Vigencia Hasta
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.vigencia_hasta}
                    onChange={(e) => setFormData({...formData, vigencia_hasta: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setFormData({
                        colegio_id: '',
                        plan: 'basico',
                        precio: 0,
                        vigencia_hasta: ''
                      });
                    }}
                    className="px-4 py-2 text-gray-600 bg-gray-200 rounded hover:bg-gray-300"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Crear
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

// Componente para gestión de actividades (Admin Colegio)
const AdminActividades = () => {
  const [actividades, setActividades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingActividad, setEditingActividad] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    fecha: '',
    horario_inicio: '',
    horario_fin: '',
    ubicacion: '',
    capacidad_maxima: '',
    costo: '',
    categoria: '',
    responsable: '',
    imagen_url: '',
    campos_personalizados: {}
  });
  const [selectedImage, setSelectedImage] = useState(null);
  const [customFields, setCustomFields] = useState([]);

  useEffect(() => {
    fetchActividades();
  }, []);

  const fetchActividades = async () => {
    try {
      const response = await axios.get(`${API}/actividades`);
      setActividades(response.data);
    } catch (error) {
      console.error('Error fetching actividades:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = async (file) => {
    if (!file) return null;
    
    setUploadLoading(true);
    try {
      const formDataUpload = new FormData();
      formDataUpload.append('file', file);
      
      const response = await axios.post(`${API}/upload/imagen`, formDataUpload, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return response.data.url;
    } catch (error) {
      console.error('Error uploading image:', error);
      alert('Error al subir la imagen');
      return null;
    } finally {
      setUploadLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    let imageUrl = formData.imagen_url;
    
    // Upload image if selected
    if (selectedImage) {
      imageUrl = await handleImageUpload(selectedImage);
      if (!imageUrl) return; // Exit if upload failed
    }

    // Prepare custom fields
    const customFieldsData = {};
    customFields.forEach(field => {
      if (field.name && field.value) {
        customFieldsData[field.name] = field.value;
      }
    });

    const dataToSend = {
      ...formData,
      imagen_url: imageUrl,
      capacidad_maxima: parseInt(formData.capacidad_maxima),
      costo: parseFloat(formData.costo),
      campos_personalizados: customFieldsData
    };

    try {
      if (editingActividad) {
        await axios.put(`${API}/actividades/${editingActividad.id}`, dataToSend);
      } else {
        await axios.post(`${API}/actividades`, dataToSend);
      }
      
      setShowModal(false);
      setEditingActividad(null);
      resetForm();
      fetchActividades();
    } catch (error) {
      console.error('Error saving actividad:', error);
      alert('Error al guardar la actividad');
    }
  };

  const resetForm = () => {
    setFormData({
      nombre: '',
      descripcion: '',
      fecha: '',
      horario_inicio: '',
      horario_fin: '',
      ubicacion: '',
      capacidad_maxima: '',
      costo: '',
      categoria: '',
      responsable: '',
      imagen_url: '',
      campos_personalizados: {}
    });
    setSelectedImage(null);
    setCustomFields([]);
  };

  const handleEdit = (actividad) => {
    setEditingActividad(actividad);
    setFormData({
      nombre: actividad.nombre,
      descripcion: actividad.descripcion,
      fecha: actividad.fecha,
      horario_inicio: actividad.horario_inicio,
      horario_fin: actividad.horario_fin,
      ubicacion: actividad.ubicacion,
      capacidad_maxima: actividad.capacidad_maxima.toString(),
      costo: actividad.costo.toString(),
      categoria: actividad.categoria,
      responsable: actividad.responsable,
      imagen_url: actividad.imagen_url || '',
      campos_personalizados: actividad.campos_personalizados || {}
    });
    
    // Load custom fields
    const loadedFields = Object.entries(actividad.campos_personalizados || {}).map(([name, value]) => ({
      name,
      value
    }));
    setCustomFields(loadedFields);
    setShowModal(true);
  };

  const handleDelete = async (actividadId) => {
    if (window.confirm('¿Está seguro de eliminar esta actividad?')) {
      try {
        await axios.delete(`${API}/actividades/${actividadId}`);
        fetchActividades();
      } catch (error) {
        console.error('Error deleting actividad:', error);
      }
    }
  };

  const addCustomField = () => {
    setCustomFields([...customFields, { name: '', value: '' }]);
  };

  const removeCustomField = (index) => {
    setCustomFields(customFields.filter((_, i) => i !== index));
  };

  const updateCustomField = (index, field, value) => {
    const updated = [...customFields];
    updated[index][field] = value;
    setCustomFields(updated);
  };

  if (loading) {
    return (
      <Layout title="Gestión de Actividades">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Gestión de Actividades">
      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Crea y administra las actividades del colegio</p>
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + Nueva Actividad
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actividad
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Fecha
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Horario
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Capacidad
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Costo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {actividades.map((actividad) => (
              <tr key={actividad.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    {actividad.imagen_url && (
                      <img 
                        src={actividad.imagen_url} 
                        alt={actividad.nombre}
                        className="h-10 w-10 rounded-full mr-3 object-cover"
                      />
                    )}
                    <div>
                      <div className="text-sm font-medium text-gray-900">{actividad.nombre}</div>
                      <div className="text-sm text-gray-500">{actividad.categoria}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(actividad.fecha).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {actividad.horario_inicio} - {actividad.horario_fin}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {actividad.capacidad_maxima}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${actividad.costo}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(actividad)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDelete(actividad.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal para crear/editar actividad */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-4/5 max-w-4xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {editingActividad ? 'Editar Actividad' : 'Nueva Actividad'}
              </h3>
              <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nombre de la Actividad
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.nombre}
                    onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Descripción
                  </label>
                  <textarea
                    rows="3"
                    required
                    value={formData.descripcion}
                    onChange={(e) => setFormData({...formData, descripcion: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fecha
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.fecha}
                    onChange={(e) => setFormData({...formData, fecha: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Ubicación
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.ubicacion}
                    onChange={(e) => setFormData({...formData, ubicacion: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hora de Inicio
                  </label>
                  <input
                    type="time"
                    required
                    value={formData.horario_inicio}
                    onChange={(e) => setFormData({...formData, horario_inicio: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hora de Fin
                  </label>
                  <input
                    type="time"
                    required
                    value={formData.horario_fin}
                    onChange={(e) => setFormData({...formData, horario_fin: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Capacidad Máxima
                  </label>
                  <input
                    type="number"
                    required
                    value={formData.capacidad_maxima}
                    onChange={(e) => setFormData({...formData, capacidad_maxima: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Costo
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formData.costo}
                    onChange={(e) => setFormData({...formData, costo: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Categoría
                  </label>
                  <select
                    required
                    value={formData.categoria}
                    onChange={(e) => setFormData({...formData, categoria: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccionar categoría</option>
                    <option value="Deportes">Deportes</option>
                    <option value="Arte">Arte</option>
                    <option value="Música">Música</option>
                    <option value="Ciencia">Ciencia</option>
                    <option value="Tecnología">Tecnología</option>
                    <option value="Idiomas">Idiomas</option>
                    <option value="Académico">Académico</option>
                    <option value="Cultural">Cultural</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Responsable
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.responsable}
                    onChange={(e) => setFormData({...formData, responsable: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Image Upload Section */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Imagen de la Actividad
                  </label>
                  <div className="flex items-center space-x-4">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setSelectedImage(e.target.files[0])}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                    {uploadLoading && (
                      <div className="text-sm text-blue-600">Subiendo...</div>
                    )}
                  </div>
                  {(formData.imagen_url || selectedImage) && (
                    <div className="mt-2">
                      <img 
                        src={selectedImage ? URL.createObjectURL(selectedImage) : formData.imagen_url} 
                        alt="Preview"
                        className="h-20 w-20 object-cover rounded"
                      />
                    </div>
                  )}
                </div>

                {/* Custom Fields Section */}
                <div className="md:col-span-2">
                  <div className="flex justify-between items-center mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Campos Personalizados
                    </label>
                    <button
                      type="button"
                      onClick={addCustomField}
                      className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200"
                    >
                      + Agregar Campo
                    </button>
                  </div>
                  {customFields.map((field, index) => (
                    <div key={index} className="flex space-x-2 mb-2">
                      <input
                        type="text"
                        placeholder="Nombre del campo"
                        value={field.name}
                        onChange={(e) => updateCustomField(index, 'name', e.target.value)}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <input
                        type="text"
                        placeholder="Valor"
                        value={field.value}
                        onChange={(e) => updateCustomField(index, 'value', e.target.value)}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        type="button"
                        onClick={() => removeCustomField(index)}
                        className="px-3 py-2 bg-red-100 text-red-800 rounded hover:bg-red-200"
                      >
                        Eliminar
                      </button>
                    </div>
                  ))}
                </div>

                <div className="md:col-span-2 flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingActividad(null);
                      resetForm();
                    }}
                    className="px-4 py-2 text-gray-600 bg-gray-200 rounded hover:bg-gray-300"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={uploadLoading}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {uploadLoading ? 'Subiendo...' : (editingActividad ? 'Actualizar' : 'Crear')}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

// Componente para gestión de comunicación (Admin Colegio)
const AdminComunicacion = () => {
  const [mensajes, setMensajes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingMessage, setEditingMessage] = useState(null);
  const [stats, setStats] = useState({});
  const [formData, setFormData] = useState({
    titulo: '',
    contenido: '',
    tipo: 'comunicado',
    prioridad: 'media',
    dirigida_a: [],
    usuarios_especificos: [],
    cursos_objetivo: [],
    requiere_confirmacion: false,
    fecha_programada: null
  });

  useEffect(() => {
    fetchMensajes();
    fetchStats();
  }, []);

  const fetchMensajes = async () => {
    try {
      const response = await axios.get(`${API}/comunicacion/mensajes`);
      setMensajes(response.data);
    } catch (error) {
      console.error('Error fetching mensajes:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/comunicacion/estadisticas`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const dataToSend = {
        ...formData,
        dirigida_a: formData.dirigida_a.filter(Boolean),
        cursos_objetivo: formData.cursos_objetivo.filter(Boolean)
      };

      if (editingMessage) {
        await axios.put(`${API}/comunicacion/mensajes/${editingMessage.id}`, dataToSend);
      } else {
        await axios.post(`${API}/comunicacion/mensajes`, dataToSend);
      }
      
      setShowModal(false);
      setEditingMessage(null);
      resetForm();
      fetchMensajes();
      fetchStats();
    } catch (error) {
      console.error('Error saving message:', error);
      alert('Error al guardar el mensaje');
    }
  };

  const resetForm = () => {
    setFormData({
      titulo: '',
      contenido: '',
      tipo: 'comunicado',
      prioridad: 'media',
      dirigida_a: [],
      usuarios_especificos: [],
      cursos_objetivo: [],
      requiere_confirmacion: false,
      fecha_programada: null
    });
  };

  const handleEdit = (mensaje) => {
    setEditingMessage(mensaje);
    setFormData({
      titulo: mensaje.titulo,
      contenido: mensaje.contenido,
      tipo: mensaje.tipo,
      prioridad: mensaje.prioridad,
      dirigida_a: mensaje.dirigida_a || [],
      usuarios_especificos: mensaje.usuarios_especificos || [],
      cursos_objetivo: mensaje.cursos_objetivo || [],
      requiere_confirmacion: mensaje.requiere_confirmacion || false,
      fecha_programada: mensaje.fecha_programada || null
    });
    setShowModal(true);
  };

  const handleSend = async (mensajeId) => {
    if (window.confirm('¿Está seguro de enviar este mensaje?')) {
      try {
        await axios.post(`${API}/comunicacion/mensajes/${mensajeId}/enviar`);
        fetchMensajes();
        fetchStats();
        alert('Mensaje enviado exitosamente');
      } catch (error) {
        console.error('Error sending message:', error);
        alert('Error al enviar el mensaje');
      }
    }
  };

  const handleDelete = async (mensajeId) => {
    if (window.confirm('¿Está seguro de eliminar este mensaje?')) {
      try {
        await axios.delete(`${API}/comunicacion/mensajes/${mensajeId}`);
        fetchMensajes();
        fetchStats();
      } catch (error) {
        console.error('Error deleting message:', error);
      }
    }
  };

  const getStatusBadge = (estado) => {
    const colors = {
      borrador: 'bg-gray-100 text-gray-800',
      enviado: 'bg-green-100 text-green-800',
      programado: 'bg-blue-100 text-blue-800',
      archivado: 'bg-yellow-100 text-yellow-800'
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityBadge = (prioridad) => {
    const colors = {
      baja: 'bg-gray-100 text-gray-800',
      media: 'bg-blue-100 text-blue-800',
      alta: 'bg-orange-100 text-orange-800',
      urgente: 'bg-red-100 text-red-800'
    };
    return colors[prioridad] || 'bg-gray-100 text-gray-800';
  };

  const getTypeBadge = (tipo) => {
    const colors = {
      circular: 'bg-purple-100 text-purple-800',
      comunicado: 'bg-blue-100 text-blue-800',
      anuncio: 'bg-green-100 text-green-800',
      notificacion: 'bg-yellow-100 text-yellow-800'
    };
    return colors[tipo] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout title="Sistema de Comunicación">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Sistema de Comunicación">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-blue-600">{stats.total_mensajes || 0}</div>
          <div className="text-gray-600 text-sm">Total Mensajes</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-green-600">{stats.mensajes_enviados || 0}</div>
          <div className="text-gray-600 text-sm">Mensajes Enviados</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-yellow-600">{stats.mensajes_borradores || 0}</div>
          <div className="text-gray-600 text-sm">Borradores</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-purple-600">{stats.tasa_lectura_promedio || 0}%</div>
          <div className="text-gray-600 text-sm">Tasa de Lectura</div>
        </div>
      </div>

      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Gestiona circulares, comunicados y anuncios</p>
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + Nuevo Mensaje
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Mensaje
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tipo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Prioridad
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Destinatarios
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {mensajes.map((mensaje) => (
              <tr key={mensaje.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{mensaje.titulo}</div>
                    <div className="text-sm text-gray-500">{new Date(mensaje.created_at).toLocaleDateString()}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTypeBadge(mensaje.tipo)}`}>
                    {mensaje.tipo}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(mensaje.estado)}`}>
                    {mensaje.estado}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getPriorityBadge(mensaje.prioridad)}`}>
                    {mensaje.prioridad}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {mensaje.total_destinatarios || 0} / {mensaje.total_leidos || 0} leídos
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {mensaje.estado === 'borrador' && (
                    <>
                      <button
                        onClick={() => handleEdit(mensaje)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleSend(mensaje.id)}
                        className="text-green-600 hover:text-green-900 mr-3"
                      >
                        Enviar
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => handleDelete(mensaje.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal para crear/editar mensaje */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-4/5 max-w-4xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {editingMessage ? 'Editar Mensaje' : 'Nuevo Mensaje'}
              </h3>
              <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Título del Mensaje
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.titulo}
                    onChange={(e) => setFormData({...formData, titulo: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Contenido
                  </label>
                  <textarea
                    rows="5"
                    required
                    value={formData.contenido}
                    onChange={(e) => setFormData({...formData, contenido: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tipo de Mensaje
                  </label>
                  <select
                    required
                    value={formData.tipo}
                    onChange={(e) => setFormData({...formData, tipo: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="comunicado">Comunicado</option>
                    <option value="circular">Circular</option>
                    <option value="anuncio">Anuncio</option>
                    <option value="notificacion">Notificación</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Prioridad
                  </label>
                  <select
                    value={formData.prioridad}
                    onChange={(e) => setFormData({...formData, prioridad: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="baja">Baja</option>
                    <option value="media">Media</option>
                    <option value="alta">Alta</option>
                    <option value="urgente">Urgente</option>
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Dirigido a (Roles)
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {['padre', 'estudiante', 'profesor', 'admin_colegio'].map(role => (
                      <label key={role} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={formData.dirigida_a.includes(role)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData({...formData, dirigida_a: [...formData.dirigida_a, role]});
                            } else {
                              setFormData({...formData, dirigida_a: formData.dirigida_a.filter(r => r !== role)});
                            }
                          }}
                          className="mr-2"
                        />
                        <span className="capitalize">{role.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.requiere_confirmacion}
                      onChange={(e) => setFormData({...formData, requiere_confirmacion: e.target.checked})}
                      className="mr-2"
                    />
                    <span className="text-sm font-medium text-gray-700">Requiere confirmación de lectura</span>
                  </label>
                </div>

                <div className="md:col-span-2 flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingMessage(null);
                      resetForm();
                    }}
                    className="px-4 py-2 text-gray-600 bg-gray-200 rounded hover:bg-gray-300"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    {editingMessage ? 'Actualizar' : 'Crear Borrador'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

// Componente para ver comunicados (Padres y otros usuarios)
const Comunicados = () => {
  const [notificaciones, setNotificaciones] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNotificaciones();
  }, []);

  const fetchNotificaciones = async () => {
    try {
      const response = await axios.get(`${API}/comunicacion/notificaciones`);
      setNotificaciones(response.data);
    } catch (error) {
      console.error('Error fetching notificaciones:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificacionId, requiresConfirmation = false) => {
    try {
      await axios.put(`${API}/comunicacion/notificaciones/${notificacionId}/leer`, {
        confirmacion: requiresConfirmation
      });
      fetchNotificaciones();
    } catch (error) {
      console.error('Error marking as read:', error);
    }
  };

  const getPriorityColor = (prioridad) => {
    const colors = {
      baja: 'border-gray-200',
      media: 'border-blue-200',
      alta: 'border-orange-200',
      urgente: 'border-red-200'
    };
    return colors[prioridad] || 'border-gray-200';
  };

  const getPriorityIcon = (prioridad) => {
    const icons = {
      baja: '📝',
      media: '📋',
      alta: '⚠️',
      urgente: '🚨'
    };
    return icons[prioridad] || '📝';
  };

  if (loading) {
    return (
      <Layout title="Comunicados">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Comunicados">
      <div className="mb-6">
        <p className="text-gray-600">Comunicados y mensajes del colegio</p>
      </div>

      <div className="space-y-6">
        {notificaciones.map((notif) => (
          <div
            key={notif.id}
            className={`bg-white rounded-lg shadow border-l-4 ${getPriorityColor(notif.mensaje_prioridad)} ${
              notif.estado === 'no_leida' ? 'border-l-blue-500' : ''
            }`}
          >
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                  <div className="text-2xl">{getPriorityIcon(notif.mensaje_prioridad)}</div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">{notif.mensaje_titulo}</h3>
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                        {notif.mensaje_tipo}
                      </span>
                      {notif.estado === 'no_leida' && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                          Nuevo
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-500 mb-2">
                      {new Date(notif.created_at).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {notif.estado === 'no_leida' && (
                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={() => markAsRead(notif.id, false)}
                    className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
                  >
                    Marcar como Leído
                  </button>
                  {notif.requiere_confirmacion && (
                    <button
                      onClick={() => markAsRead(notif.id, true)}
                      className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700"
                    >
                      Confirmar Lectura
                    </button>
                  )}
                </div>
              )}

              {notif.estado === 'leida' && (
                <div className="mt-4 text-sm text-gray-500">
                  ✓ Leído el {new Date(notif.fecha_leido).toLocaleDateString()}
                  {notif.confirmado && ' • Confirmado'}
                </div>
              )}
            </div>
          </div>
        ))}

        {notificaciones.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📭</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No hay comunicados</h2>
            <p className="text-gray-600">No tienes comunicados pendientes por leer</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

// Página temporal para rutas no implementadas
const ComingSoon = ({ title }) => (
  <Layout title={title}>
    <div className="text-center py-12">
      <div className="text-6xl mb-4">🚧</div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">En Desarrollo</h2>
      <p className="text-gray-600">Esta funcionalidad estará disponible pronto</p>
    </div>
  </Layout>
);

// Componente principal de la aplicación
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

          {/* Rutas Admin Global */}
          <Route 
            path="/global/colegios" 
            element={
              <ProtectedRoute allowedRoles={['admin_global']}>
                <GlobalColegios />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/global/reportes" 
            element={
              <ProtectedRoute allowedRoles={['admin_global']}>
                <GlobalReportes />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/global/suscripciones" 
            element={
              <ProtectedRoute allowedRoles={['admin_global']}>
                <GlobalSuscripciones />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/global/usuarios" 
            element={
              <ProtectedRoute allowedRoles={['admin_global']}>
                <GlobalUsuarios />
              </ProtectedRoute>
            } 
          />

          {/* Rutas para Administrador de Colegio */}
          <Route 
            path="/admin/actividades" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <AdminActividades />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/estudiantes" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <ComingSoon title="Gestión de Estudiantes" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/pagos" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <ComingSoon title="Gestión de Pagos" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/inscripciones" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <ComingSoon title="Gestión de Inscripciones" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/reportes" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <ComingSoon title="Reportes" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/comunicacion" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <ComingSoon title="Comunicación" />
              </ProtectedRoute>
            } 
          />
          
          {/* Rutas para Padres */}
          <Route 
            path="/actividades" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <ComingSoon title="Actividades del Colegio" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/mis-hijos" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <ComingSoon title="Mis Hijos" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/mis-inscripciones" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <ComingSoon title="Mis Inscripciones" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/mis-pagos" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <MisPagosPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/comunicados" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <ComingSoon title="Comunicados" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/calendario" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <ComingSoon title="Calendario" />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/notificaciones" 
            element={
              <ProtectedRoute>
                <ComingSoon title="Notificaciones" />
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