# SalesIA Enterprise

Aplicación empresarial de ventas basada en el plan técnico del proyecto. Incluye frontend React/TypeScript, API FastAPI y persistencia SQLAlchemy para PostgreSQL (SQLite local como alternativa de desarrollo).

## Estructura

- `frontend/`: React + TypeScript + Vite y UI empresarial.
- `backend/`: FastAPI, modelos relacionales, validaciones y endpoints REST.
- `render.yaml`: blueprint de API y PostgreSQL para Render.
- `vercel.json`: build y rutas SPA para Vercel.
- `.env.example`: variables de entorno de referencia.

## Ejecutar localmente

### Backend
Requiere Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

La API crea las tablas y carga clientes/productos de demostración en el primer arranque. Documentación interactiva: http://localhost:8000/docs. Salud: http://localhost:8000/health.

### Frontend
En otra terminal:

```bash
cd frontend
npm install
# PowerShell: $env:VITE_API_URL="http://localhost:8000"
# macOS/Linux: export VITE_API_URL=http://localhost:8000
npm run dev
```

Vite mostrará la URL local, habitualmente http://localhost:5173. Si `VITE_API_URL` está vacío, el frontend conserva el modo demostración local.

## Endpoints iniciales

- `GET/POST /customers`: listar/buscar y crear clientes.
- `GET/POST /products`: catálogo y creación de productos.
- `GET/POST /sales`: consulta y registro transaccional de ventas.
- `GET /dashboard/summary`: indicadores derivados de datos guardados.
- `GET /analytics/summary`: conteo, ingresos, media y mediana.
- `POST /probability/bayes`: cálculo de Bayes.
- `GET /insights`: alertas explicables de stock y pagos pendientes.
- `GET /inventory/movements`: trazabilidad de movimientos.
- `GET /reports/sales.csv`: exportación CSV de ventas.
- `GET /audit`: historial de acciones registradas.

Al registrar una venta, la API valida cliente, productos, cantidades, stock y descuento; calcula subtotal, impuesto y total; guarda cabecera y detalle, crea un pago pendiente, registra movimientos de inventario y auditoría en una transacción de base de datos.

## GitHub + Render + Vercel

### 1. GitHub
1. Descomprime el proyecto y abre una terminal dentro de `SalesIA_Enterprise`.
2. Ejecuta:

```bash
git init
git add .
git commit -m "SalesIA Enterprise full stack initial"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/TU-REPOSITORIO.git
git push -u origin main
```

Crea primero un repositorio vacío en GitHub y sustituye la URL de ejemplo. No subas contraseñas ni archivos `.env`.

### 2. Render (API y PostgreSQL)
1. En Render, selecciona **New → Blueprint** y conecta el repositorio. Render detectará `render.yaml`.
2. Revisa y crea el servicio web y la base PostgreSQL. Para conservar los datos a largo plazo, selecciona un plan de base de datos persistente disponible en tu cuenta; no uses una base temporal para producción.
3. Cuando el servicio esté desplegado, verifica `https://TU-SERVICIO.onrender.com/health` y `/docs`.
4. Si ajustas el dominio del frontend, configura `CORS_ORIGINS` con el dominio exacto de Vercel. `CORS_ORIGIN_REGEX` admite dominios `*.vercel.app`.

### 3. Vercel (frontend)
1. En Vercel, importa el mismo repositorio GitHub.
2. Configura el directorio raíz como `frontend` si Vercel no toma el `vercel.json` de la raíz; el comando de build es `npm run build` y la salida `dist` en ese caso. Si usas la configuración de raíz incluida, conserva el `vercel.json` de la raíz.
3. En **Settings → Environment Variables**, agrega `VITE_API_URL` con la URL HTTPS del backend de Render, sin barra final. Ejemplo: `https://salesia-enterprise-api.onrender.com`.
4. Despliega de nuevo después de agregar la variable.

## Variables de entorno del backend

- `DATABASE_URL`: cadena de conexión PostgreSQL. Render la inyecta desde la base definida en `render.yaml`.
- `CORS_ORIGINS`: dominios permitidos separados por comas; agrega el dominio de producción de Vercel.
- `CORS_ORIGIN_REGEX`: expresión regular de orígenes permitidos para previews de Vercel.

## Estado y límites importantes

Este paquete es una base full-stack inicial, no un sistema fiscal certificado ni un despliegue de producción auditado. El backend persiste clientes, productos, ventas, detalle, pagos pendientes, inventario y auditoría. La UI ya consulta clientes/productos/ventas y envía las ventas al backend cuando `VITE_API_URL` está configurada. Otras tarjetas y pantallas del frontend aún conservan elementos visuales/datos de demostración y deben conectarse gradualmente a sus endpoints.

Antes de operar con información real se debe implementar y probar autenticación/autorización por roles, recuperación de contraseña, protección contra abuso, migraciones de base de datos, política de respaldos, gestión de pagos, reglas tributarias definitivas y cualquier integración autorizada con SUNAT. La API no emite facturas electrónicas oficiales ni consulta SUNAT. Cambia los datos de ejemplo por datos propios antes de usarlo comercialmente.


## Flujo comercial integrado

- **Ventas:** registra operaciones desde el catálogo y los clientes, con cálculo de subtotal, descuento e IGV.
- **Acciones por venta:** el menú de tres puntos permite marcar una venta pendiente como pagada, anularla o copiar su número.
- **Movimientos:** vista centralizada de las operaciones con filtros por estado y búsqueda; permite exportar CSV.
- **Anulación con backend:** una venta anulada devuelve las cantidades al inventario y genera movimientos de reversión y auditoría. Las ventas anuladas no se pueden reactivar; se debe crear una nueva operación.
- **Bayes:** la calculadora envía los parámetros a `POST /probability/bayes` cuando `VITE_API_URL` está configurada.
- **Reportes de ventas:** `GET /reports/sales.csv` exporta las operaciones persistidas.
- **Analítica:** los endpoints `/dashboard/summary`, `/analytics/summary` e `/insights` exponen indicadores basados en la base de datos.

### Configuración local

1. Backend: instalar las dependencias de `backend/requirements.txt` y ejecutar `uvicorn app.main:app --reload` desde `backend/`.
2. Frontend: copiar `frontend/.env.example` a `frontend/.env`, configurar `VITE_API_URL` con la URL del backend, instalar dependencias y ejecutar `npm run dev`.
3. Para datos persistentes en producción, configurar `DATABASE_URL` en el backend con PostgreSQL. Sin API configurada, el frontend conserva un modo local de demostración y sus cambios no se guardan en el servidor.
