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
    // Cargar colegios para el selector
    const loadColegios = async () => {
      try {
        // Por ahora crear uno de ejemplo
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

// Componente Dashboard principal
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
          </>
        )}
      </div>
    </Layout>
  );
};

// Página de Gestión de Actividades (SOLO Admin Colegio)
const AdminActividadesPage = () => {
  const [actividades, setActividades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingActivity, setEditingActivity] = useState(null);

  useEffect(() => {
    loadActividades();
  }, []);

  const loadActividades = async () => {
    try {
      const response = await axios.get(`${API}/actividades`);
      setActividades(response.data);
    } catch (error) {
      console.error('Error cargando actividades:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (actividad) => {
    setEditingActivity(actividad);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('¿Estás seguro de eliminar esta actividad?')) {
      try {
        await axios.delete(`${API}/actividades/${id}`);
        loadActividades();
      } catch (error) {
        alert('Error eliminando actividad: ' + error.response?.data?.detail);
      }
    }
  };

  const getEstadoBadge = (estado) => {
    const colors = {
      'pendiente': 'bg-yellow-100 text-yellow-800',
      'confirmada': 'bg-green-100 text-green-800',
      'cancelada': 'bg-red-100 text-red-800',
      'reprogramada': 'bg-blue-100 text-blue-800'
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout title="Gestión de Actividades">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Gestión de Actividades">
      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Administra las actividades del colegio</p>
        <button
          onClick={() => {
            setEditingActivity(null);
            setShowForm(true);
          }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          + Nueva Actividad
        </button>
      </div>

      {showForm && (
        <FormularioActividad
          actividad={editingActivity}
          onSave={() => {
            setShowForm(false);
            setEditingActivity(null);
            loadActividades();
          }}
          onCancel={() => {
            setShowForm(false);
            setEditingActivity(null);
          }}
        />
      )}

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
                Estado
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cupo
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
                  <div>
                    <div className="text-sm font-medium text-gray-900">{actividad.nombre}</div>
                    <div className="text-sm text-gray-500">{actividad.responsable}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(actividad.fecha_inicio).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getEstadoBadge(actividad.estado)}`}>
                    {actividad.estado}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {actividad.participantes_confirmados} / {actividad.cupo_maximo || '∞'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${actividad.costo_estudiante}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  <button
                    onClick={() => handleEdit(actividad)}
                    className="text-indigo-600 hover:text-indigo-900"
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
        
        {actividades.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No hay actividades creadas aún</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

// Página de Actividades para Padres (Vista de Catálogo)
const ActividadesPadresPage = () => {
  const [actividades, setActividades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState(null);
  const [misHijos, setMisHijos] = useState([]);

  useEffect(() => {
    loadActividadesDisponibles();
    loadMisHijos();
  }, []);

  const loadActividadesDisponibles = async () => {
    try {
      // Solo cargar actividades confirmadas
      const response = await axios.get(`${API}/actividades?estado=confirmada`);
      setActividades(response.data);
    } catch (error) {
      console.error('Error cargando actividades:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMisHijos = async () => {
    try {
      const response = await axios.get(`${API}/estudiantes`);
      setMisHijos(response.data);
    } catch (error) {
      console.error('Error cargando hijos:', error);
    }
  };

  const handleInscripcion = (actividad) => {
    setSelectedActivity(actividad);
  };

  if (loading) {
    return (
      <Layout title="Actividades del Colegio">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Actividades del Colegio">
      <div className="mb-6">
        <p className="text-gray-600">Descubre las actividades disponibles para tus hijos</p>
      </div>

      {actividades.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🎈</div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">No hay actividades disponibles</h3>
          <p className="text-gray-600">Próximamente habrá nuevas actividades emocionantes</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {actividades.map((actividad) => (
            <div key={actividad.id} className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow">
              {/* Imagen placeholder */}
              <div className="h-48 bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center">
                <div className="text-white text-4xl">🎭</div>
              </div>
              
              <div className="p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-2">{actividad.nombre}</h3>
                <p className="text-gray-600 mb-4 line-clamp-2">{actividad.descripcion}</p>
                
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-gray-600">
                    <span className="mr-2">📅</span>
                    {new Date(actividad.fecha_inicio).toLocaleDateString('es-ES', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <span className="mr-2">⏰</span>
                    {new Date(actividad.fecha_inicio).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })} - {new Date(actividad.fecha_fin).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <span className="mr-2">👥</span>
                    Cursos: {actividad.cursos_participantes.join(', ')}
                  </div>
                  {actividad.costo_estudiante > 0 && (
                    <div className="flex items-center text-sm text-gray-600">
                      <span className="mr-2">💰</span>
                      ${actividad.costo_estudiante}
                    </div>
                  )}
                  {actividad.cupo_maximo && (
                    <div className="flex items-center text-sm text-gray-600">
                      <span className="mr-2">🎫</span>
                      {actividad.participantes_confirmados} / {actividad.cupo_maximo} inscritos
                    </div>
                  )}
                </div>

                <button
                  onClick={() => handleInscripcion(actividad)}
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-2 px-4 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-colors font-semibold"
                  data-testid={`inscribir-actividad-${actividad.id}`}
                >
                  Ver Detalles e Inscribir
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal de detalles e inscripción */}
      {selectedActivity && (
        <DetalleInscripcionModal
          actividad={selectedActivity}
          misHijos={misHijos}
          onClose={() => setSelectedActivity(null)}
          onInscripcion={() => {
            setSelectedActivity(null);
            loadActividadesDisponibles();
          }}
        />
      )}
    </Layout>
  );
};

// Página "Mis Inscripciones" para Padres
const MisInscripcionesPage = () => {
  const [inscripciones, setInscripciones] = useState([]);
  const [actividades, setActividades] = useState({});
  const [estudiantes, setEstudiantes] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMisInscripciones();
  }, []);

  const loadMisInscripciones = async () => {
    try {
      // Cargar inscripciones
      const inscripcionesResponse = await axios.get(`${API}/inscripciones`);
      const inscripcionesData = inscripcionesResponse.data;
      
      // Cargar actividades para obtener detalles
      const actividadesResponse = await axios.get(`${API}/actividades`);
      const actividadesMap = {};
      actividadesResponse.data.forEach(act => {
        actividadesMap[act.id] = act;
      });
      
      // Cargar estudiantes para obtener nombres
      const estudiantesResponse = await axios.get(`${API}/estudiantes`);
      const estudiantesMap = {};
      estudiantesResponse.data.forEach(est => {
        estudiantesMap[est.id] = est;
      });
      
      setInscripciones(inscripcionesData);
      setActividades(actividadesMap);
      setEstudiantes(estudiantesMap);
    } catch (error) {
      console.error('Error cargando inscripciones:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEstadoBadge = (estado) => {
    const colors = {
      'pendiente': 'bg-yellow-100 text-yellow-800',
      'confirmada': 'bg-green-100 text-green-800',
      'pago_pendiente': 'bg-orange-100 text-orange-800',
      'cancelada': 'bg-red-100 text-red-800'
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  const getEstadoLabel = (estado) => {
    const labels = {
      'pendiente': 'Pendiente',
      'confirmada': 'Confirmada',
      'pago_pendiente': 'Pago Pendiente',
      'cancelada': 'Cancelada'
    };
    return labels[estado] || estado;
  };

  if (loading) {
    return (
      <Layout title="Mis Inscripciones">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-orange-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Mis Inscripciones">
      <div className="mb-6">
        <p className="text-gray-600">Revisa el estado de las inscripciones de tus hijos</p>
      </div>

      {inscripciones.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📋</div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">No hay inscripciones aún</h3>
          <p className="text-gray-600 mb-4">Inscribe a tus hijos en las actividades del colegio</p>
          <Link
            to="/actividades"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Ver Actividades
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {inscripciones.map((inscripcion) => {
            const actividad = actividades[inscripcion.actividad_id];
            const estudiante = estudiantes[inscripcion.estudiante_id];
            
            if (!actividad || !estudiante) return null;

            return (
              <div key={inscripcion.id} className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center mb-2">
                      <h3 className="text-lg font-semibold text-gray-900 mr-3">
                        {actividad.nombre}
                      </h3>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getEstadoBadge(inscripcion.estado)}`}>
                        {getEstadoLabel(inscripcion.estado)}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                      <div>
                        <p><span className="font-medium">Estudiante:</span> {estudiante.nombre_completo}</p>
                        <p><span className="font-medium">Curso:</span> {estudiante.curso_grado}</p>
                        <p><span className="font-medium">Fecha:</span> {new Date(actividad.fecha_inicio).toLocaleDateString('es-ES')}</p>
                      </div>
                      <div>
                        <p><span className="font-medium">Responsable:</span> {actividad.responsable}</p>
                        {actividad.costo_estudiante > 0 && (
                          <p><span className="font-medium">Costo:</span> ${actividad.costo_estudiante}</p>
                        )}
                        <p><span className="font-medium">Inscrito:</span> {new Date(inscripcion.created_at).toLocaleDateString('es-ES')}</p>
                      </div>
                    </div>

                    {inscripcion.comentarios && (
                      <div className="mt-3 p-3 bg-gray-50 rounded">
                        <p className="text-sm text-gray-700">
                          <span className="font-medium">Comentario:</span> {inscripcion.comentarios}
                        </p>
                      </div>
                    )}
                  </div>

                  {inscripcion.estado === 'pago_pendiente' && (
                    <div className="ml-4">
                      <button className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 text-sm">
                        Realizar Pago
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Layout>
  );
};

// Página "Mis Hijos" para Padres
const MisHijosPage = () => {
  const [misHijos, setMisHijos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);

  useEffect(() => {
    loadMisHijos();
  }, []);

  const loadMisHijos = async () => {
    try {
      const response = await axios.get(`${API}/estudiantes`);
      setMisHijos(response.data);
    } catch (error) {
      console.error('Error cargando hijos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (estudiante) => {
    setEditingStudent(estudiante);
    setShowForm(true);
  };

  if (loading) {
    return (
      <Layout title="Mis Hijos">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-purple-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Mis Hijos">
      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Gestiona la información de tus hijos</p>
        <button
          onClick={() => {
            setEditingStudent(null);
            setShowForm(true);
          }}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
          data-testid="agregar-hijo-btn"
        >
          + Agregar Hijo
        </button>
      </div>

      {showForm && (
        <FormularioEstudiante
          estudiante={editingStudent}
          onSave={() => {
            setShowForm(false);
            setEditingStudent(null);
            loadMisHijos();
          }}
          onCancel={() => {
            setShowForm(false);
            setEditingStudent(null);
          }}
        />
      )}

      {misHijos.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">👶</div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">No has agregado hijos aún</h3>
          <p className="text-gray-600">Agrega la información de tus hijos para inscribirlos en actividades</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {misHijos.map((hijo) => (
            <div key={hijo.id} className="bg-white rounded-lg shadow p-6">
              <div className="text-center mb-4">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-2xl">👧</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900">{hijo.nombre_completo}</h3>
                <p className="text-gray-600">{hijo.curso_grado}</p>
              </div>

              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Fecha de Nacimiento:</span>
                  <span>{new Date(hijo.fecha_nacimiento).toLocaleDateString('es-ES')}</span>
                </div>
                <div className="flex justify-between">
                  <span>Edad:</span>
                  <span>{Math.floor((new Date() - new Date(hijo.fecha_nacimiento)) / (365.25 * 24 * 60 * 60 * 1000))} años</span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t flex space-x-2">
                <button
                  onClick={() => handleEdit(hijo)}
                  className="flex-1 bg-gray-100 text-gray-700 py-2 px-3 rounded hover:bg-gray-200 text-sm"
                  data-testid={`editar-hijo-${hijo.id}`}
                >
                  Editar
                </button>
                <button className="flex-1 bg-blue-600 text-white py-2 px-3 rounded hover:bg-blue-700 text-sm">
                  Ver Actividades
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
};

// Gestión de Estudiantes (Admin)
const AdminEstudiantesPage = () => {
  const [estudiantes, setEstudiantes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);

  useEffect(() => {
    loadEstudiantes();
  }, []);

  const loadEstudiantes = async () => {
    try {
      const response = await axios.get(`${API}/estudiantes`);
      setEstudiantes(response.data);
    } catch (error) {
      console.error('Error cargando estudiantes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (estudiante) => {
    setEditingStudent(estudiante);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('¿Estás seguro de eliminar este estudiante?')) {
      try {
        // Implementar delete endpoint
        alert('Funcionalidad de eliminar pendiente por implementar');
      } catch (error) {
        alert('Error eliminando estudiante');
      }
    }
  };

  if (loading) {
    return (
      <Layout title="Gestión de Estudiantes">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-green-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Gestión de Estudiantes">
      <div className="mb-6 flex justify-between items-center">
        <p className="text-gray-600">Administra los estudiantes del colegio</p>
        <button
          onClick={() => {
            setEditingStudent(null);
            setShowForm(true);
          }}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
        >
          + Nuevo Estudiante
        </button>
      </div>

      {showForm && (
        <FormularioEstudiante
          estudiante={editingStudent}
          isAdmin={true}
          onSave={() => {
            setShowForm(false);
            setEditingStudent(null);
            loadEstudiantes();
          }}
          onCancel={() => {
            setShowForm(false);
            setEditingStudent(null);
          }}
        />
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estudiante
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Curso
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Edad
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Padre
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {estudiantes.map((estudiante) => (
              <tr key={estudiante.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                        <span className="text-lg">👧</span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">{estudiante.nombre_completo}</div>
                      <div className="text-sm text-gray-500">{new Date(estudiante.fecha_nacimiento).toLocaleDateString('es-ES')}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {estudiante.curso_grado}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {Math.floor((new Date() - new Date(estudiante.fecha_nacimiento)) / (365.25 * 24 * 60 * 60 * 1000))} años
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {estudiante.padre_id || 'No asignado'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  <button
                    onClick={() => handleEdit(estudiante)}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDelete(estudiante.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {estudiantes.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No hay estudiantes registrados aún</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

// Modal para detalles e inscripción de actividad
const DetalleInscripcionModal = ({ actividad, misHijos, onClose, onInscripcion }) => {
  const [selectedHijo, setSelectedHijo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleInscribir = async () => {
    if (!selectedHijo) {
      setError('Selecciona un hijo para inscribir');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await axios.post(`${API}/inscripciones`, {
        actividad_id: actividad.id,
        estudiante_id: selectedHijo,
        comentarios: 'Inscripción desde interfaz de padres'
      });

      alert('¡Inscripción exitosa! Recibirás información sobre el pago si es necesario.');
      onInscripcion();
    } catch (error) {
      setError(error.response?.data?.detail || 'Error en la inscripción');
    } finally {
      setLoading(false);
    }
  };

  const hijoElegible = (hijo) => {
    return actividad.cursos_participantes.length === 0 || 
           actividad.cursos_participantes.includes(hijo.curso_grado);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="modal-detalle-inscripcion">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-2xl font-bold text-gray-900">{actividad.nombre}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
              data-testid="cerrar-modal-btn"
            >
              ×
            </button>
          </div>

          {/* Imagen de la actividad */}
          <div className="h-64 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center mb-6">
            <div className="text-white text-6xl">🎭</div>
          </div>

          <div className="space-y-4 mb-6">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Descripción</h3>
              <p className="text-gray-600">{actividad.descripcion}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">📅 Fecha y Hora</h3>
                <p className="text-gray-600">
                  {new Date(actividad.fecha_inicio).toLocaleDateString('es-ES', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </p>
                <p className="text-gray-600">
                  {new Date(actividad.fecha_inicio).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })} - {new Date(actividad.fecha_fin).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
              
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">👤 Responsable</h3>
                <p className="text-gray-600">{actividad.responsable}</p>
              </div>
            </div>

            {actividad.materiales_requeridos.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">📝 Materiales Necesarios</h3>
                <ul className="list-disc list-inside text-gray-600">
                  {actividad.materiales_requeridos.map((material, index) => (
                    <li key={index}>{material}</li>
                  ))}
                </ul>
              </div>
            )}

            {actividad.costo_estudiante > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h3 className="font-semibold text-yellow-800 mb-2">💰 Información de Pago</h3>
                <p className="text-yellow-700">
                  Costo por estudiante: <span className="font-bold">${actividad.costo_estudiante}</span>
                </p>
                <p className="text-yellow-600 text-sm mt-1">
                  El pago se procesará después de confirmar la inscripción
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <div className="mb-6">
            <h3 className="font-semibold text-gray-900 mb-3">Selecciona el hijo a inscribir:</h3>
            <div className="space-y-2">
              {misHijos.filter(hijoElegible).map((hijo) => (
                <label key={hijo.id} className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="radio"
                    name="hijo"
                    value={hijo.id}
                    checked={selectedHijo === hijo.id}
                    onChange={(e) => setSelectedHijo(e.target.value)}
                    className="mr-3"
                    data-testid={`hijo-option-${hijo.id}`}
                  />
                  <div>
                    <div className="font-medium">{hijo.nombre_completo}</div>
                    <div className="text-sm text-gray-600">{hijo.curso_grado}</div>
                  </div>
                </label>
              ))}
            </div>
            
            {misHijos.filter(hijoElegible).length === 0 && (
              <p className="text-gray-500 text-center py-4">
                Ninguno de tus hijos es elegible para esta actividad (curso no coincide)
              </p>
            )}
          </div>

          <div className="flex justify-end space-x-4">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleInscribir}
              disabled={loading || !selectedHijo || misHijos.filter(hijoElegible).length === 0}
              className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 font-semibold"
              data-testid="confirmar-inscripcion-btn"
            >
              {loading ? 'Inscribiendo...' : 'Confirmar Inscripción'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Formulario para agregar/editar estudiantes
const FormularioEstudiante = ({ estudiante, isAdmin = false, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    nombre_completo: '',
    fecha_nacimiento: '',
    curso_grado: '',
    padre_id: '',
    informacion_medica: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (estudiante) {
      setFormData({
        nombre_completo: estudiante.nombre_completo || '',
        fecha_nacimiento: estudiante.fecha_nacimiento ? 
          (typeof estudiante.fecha_nacimiento === 'string' ? 
            estudiante.fecha_nacimiento.split('T')[0] : 
            estudiante.fecha_nacimiento.toISOString().split('T')[0]) : '',
        curso_grado: estudiante.curso_grado || '',
        padre_id: estudiante.padre_id || '',
        informacion_medica: estudiante.informacion_medica ? 
          (typeof estudiante.informacion_medica === 'object' ? 
            JSON.stringify(estudiante.informacion_medica) : 
            estudiante.informacion_medica) : ''
      });
    }
  }, [estudiante]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const payload = {
        ...formData,
        informacion_medica: formData.informacion_medica ? 
          { notas: formData.informacion_medica } : null
      };

      if (estudiante) {
        // Actualizar - endpoint pendiente por implementar
        alert('Funcionalidad de editar pendiente por implementar');
      } else {
        await axios.post(`${API}/estudiantes`, payload);
      }

      onSave();
    } catch (error) {
      setError(error.response?.data?.detail || 'Error al guardar el estudiante');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">
            {estudiante ? 'Editar Estudiante' : 'Agregar Estudiante'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre Completo *
              </label>
              <input
                type="text"
                name="nombre_completo"
                value={formData.nombre_completo}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
                data-testid="nombre-completo-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha de Nacimiento *
              </label>
              <input
                type="date"
                name="fecha_nacimiento"
                value={formData.fecha_nacimiento}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
                data-testid="fecha-nacimiento-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Curso/Grado *
              </label>
              <select
                name="curso_grado"
                value={formData.curso_grado}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
                data-testid="curso-grado-select"
              >
                <option value="">Selecciona un curso</option>
                <option value="Pre-Kinder">Pre-Kinder</option>
                <option value="Kinder">Kinder</option>
                <option value="1ro A">1ro A</option>
                <option value="1ro B">1ro B</option>
                <option value="2do A">2do A</option>
                <option value="2do B">2do B</option>
                <option value="3ro A">3ro A</option>
                <option value="3ro B">3ro B</option>
                <option value="4to A">4to A</option>
                <option value="4to B">4to B</option>
                <option value="5to A">5to A</option>
                <option value="5to B">5to B</option>
                <option value="6to A">6to A</option>
                <option value="6to B">6to B</option>
              </select>
            </div>

            {isAdmin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ID del Padre
                </label>
                <input
                  type="text"
                  name="padre_id"
                  value={formData.padre_id}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Opcional - ID del padre/tutor"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Información Médica
              </label>
              <textarea
                name="informacion_medica"
                value={formData.informacion_medica}
                onChange={handleChange}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Alergias, medicamentos, condiciones especiales..."
              />
            </div>

            <div className="flex justify-end space-x-4 pt-4 border-t">
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                data-testid="guardar-estudiante-btn"
              >
                {loading ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Formulario para crear/editar actividades (SOLO para admin)
const FormularioActividad = ({ actividad, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    fecha_inicio: '',
    fecha_fin: '',
    cursos_participantes: '',
    cupo_maximo: '',
    costo_estudiante: '0',
    materiales_requeridos: '',
    visibilidad: 'interna',
    responsable: '',
    metodos_pago: ['efectivo'],
    es_permanente: false,
    requiere_validacion_manual: false
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (actividad) {
      setFormData({
        nombre: actividad.nombre || '',
        descripcion: actividad.descripcion || '',
        fecha_inicio: actividad.fecha_inicio ? actividad.fecha_inicio.slice(0, 16) : '',
        fecha_fin: actividad.fecha_fin ? actividad.fecha_fin.slice(0, 16) : '',
        cursos_participantes: actividad.cursos_participantes?.join(', ') || '',
        cupo_maximo: actividad.cupo_maximo || '',
        costo_estudiante: actividad.costo_estudiante || '0',
        materiales_requeridos: actividad.materiales_requeridos?.join(', ') || '',
        visibilidad: actividad.visibilidad || 'interna',
        responsable: actividad.responsable || '',
        metodos_pago: actividad.metodos_pago || ['efectivo'],
        es_permanente: actividad.es_permanente || false,
        requiere_validacion_manual: actividad.requiere_validacion_manual || false
      });
    }
  }, [actividad]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const payload = {
        ...formData,
        cursos_participantes: formData.cursos_participantes.split(',').map(c => c.trim()).filter(c => c),
        materiales_requeridos: formData.materiales_requeridos.split(',').map(m => m.trim()).filter(m => m),
        cupo_maximo: formData.cupo_maximo ? parseInt(formData.cupo_maximo) : null,
        costo_estudiante: parseFloat(formData.costo_estudiante) || 0
      };

      if (actividad) {
        await axios.put(`${API}/actividades/${actividad.id}`, payload);
      } else {
        await axios.post(`${API}/actividades`, payload);
      }

      onSave();
    } catch (error) {
      setError(error.response?.data?.detail || 'Error al guardar la actividad');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">
            {actividad ? 'Editar Actividad' : 'Nueva Actividad'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre de la Actividad *
              </label>
              <input
                type="text"
                name="nombre"
                value={formData.nombre}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Descripción
              </label>
              <textarea
                name="descripcion"
                value={formData.descripcion}
                onChange={handleChange}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha de Inicio *
                </label>
                <input
                  type="datetime-local"
                  name="fecha_inicio"
                  value={formData.fecha_inicio}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha de Fin *
                </label>
                <input
                  type="datetime-local"
                  name="fecha_fin"
                  value={formData.fecha_fin}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cursos Participantes (separados por coma)
              </label>
              <input
                type="text"
                name="cursos_participantes"
                value={formData.cursos_participantes}
                onChange={handleChange}
                placeholder="Ej: 3ro A, 3ro B, 4to A"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cupo Máximo
                </label>
                <input
                  type="number"
                  name="cupo_maximo"
                  value={formData.cupo_maximo}
                  onChange={handleChange}
                  min="1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Costo por Estudiante
                </label>
                <input
                  type="number"
                  name="costo_estudiante"
                  value={formData.costo_estudiante}
                  onChange={handleChange}
                  min="0"
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Responsable
              </label>
              <input
                type="text"
                name="responsable"
                value={formData.responsable}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Materiales Requeridos (separados por coma)
              </label>
              <input
                type="text"
                name="materiales_requeridos"
                value={formData.materiales_requeridos}
                onChange={handleChange}
                placeholder="Ej: Calculadora, Cuaderno, Lápiz"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Visibilidad
              </label>
              <select
                name="visibilidad"
                value={formData.visibilidad}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="interna">Interna (Solo estudiantes del colegio)</option>
                <option value="externa">Externa (Abierta al público)</option>
                <option value="mixta">Mixta (Estudiantes + externos)</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="es_permanente"
                  checked={formData.es_permanente}
                  onChange={handleChange}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Actividad permanente</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="requiere_validacion_manual"
                  checked={formData.requiere_validacion_manual}
                  onChange={handleChange}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Requiere validación manual</span>
              </label>
            </div>

            <div className="flex justify-end space-x-4 pt-4 border-t">
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
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
          
          {/* Rutas para Administrador de Colegio */}
          <Route 
            path="/admin/actividades" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <AdminActividadesPage />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/admin/estudiantes" 
            element={
              <ProtectedRoute allowedRoles={['admin_colegio']}>
                <AdminEstudiantesPage />
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
          
          {/* Rutas para Padres */}
          <Route 
            path="/actividades" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <ActividadesPadresPage />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/mis-hijos" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <MisHijosPage />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/mis-inscripciones" 
            element={
              <ProtectedRoute allowedRoles={['padre']}>
                <MisInscripcionesPage />
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