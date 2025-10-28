-- Archivo ejecutado automáticamente al crear el contenedor postgres (docker-entrypoint-initdb.d)
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
