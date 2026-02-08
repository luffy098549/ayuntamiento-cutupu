from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import psycopg2  # <-- PostgreSQL en lugar de sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
import random
import string
import json
import csv
from io import BytesIO
import logging

# Configurar logging para Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'cutupu-secret-key-123'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

# ===============================
# CONEXIÓN A POSTGRESQL PARA RENDER (CORREGIDO)
# ===============================

# URL de Render - CON SSL OBLIGATORIO
DATABASE_URL = "postgresql://ayuntamiento:qCKauldXNtrUabI8w8hHU6M9VphgjsfE@dpg-d64dt7ngi27c73avjru0-a/ayuntamiento_8npe"

def get_db():
    """Conectar a PostgreSQL - VERSIÓN PARA RENDER CON SSL"""
    try:
        # CONEXIÓN CON SSL PARA RENDER (OBLIGATORIO)
        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode='require',  # ← ¡ESTO ES CRÍTICO PARA RENDER!
            connect_timeout=10
        )
        logger.info("✅ Conectado a PostgreSQL en Render con SSL")
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL (con SSL): {e}")
        # Intentar sin SSL para desarrollo local
        try:
            conn = psycopg2.connect(DATABASE_URL)
            logger.info("✅ Conectado a PostgreSQL (sin SSL - modo desarrollo)")
            return conn
        except Exception as e2:
            logger.error(f"❌ Error conectando a PostgreSQL (sin SSL): {e2}")
            raise

def dict_fetchall(cursor):
    """Convertir resultados a diccionario"""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def dict_fetchone(cursor):
    """Convertir un resultado a diccionario"""
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None

# ===============================
# CONFIGURACIÓN
# ===============================

ADMIN_EMAIL = 'admin@ayuntamiento.gob'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def verificar_y_preparar_db():
    """Crear todas las tablas necesarias en PostgreSQL - VERSIÓN MEJORADA"""
    logger.info("🔧 Inicializando PostgreSQL para Render...")
    
    try:
        # Conectar a PostgreSQL
        conn = get_db()
        cur = conn.cursor()
        
        logger.info("✅ Conectado a PostgreSQL en Render")
        
        # 1. Tabla USUARIOS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telefono TEXT,
            direccion TEXT,
            cedula TEXT,
            rol_id INTEGER DEFAULT 2,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT TRUE
        )
        """)
        logger.info("✅ Tabla 'usuarios' creada/verificada")
        
        # 2. Tabla REPORTES
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reportes (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            categoria TEXT NOT NULL,
            ubicacion TEXT NOT NULL,
            latitud REAL,
            longitud REAL,
            estado TEXT DEFAULT 'pendiente',
            prioridad TEXT DEFAULT 'media',
            fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            imagen TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        """)
        logger.info("✅ Tabla 'reportes' creada/verificada")
        
        # 3. Tabla DENUNCIAS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS denuncias (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            tipo TEXT NOT NULL,
            denunciado_nombre TEXT,
            denunciado_cargo TEXT,
            denunciado_institucion TEXT,
            pruebas TEXT,
            estado TEXT DEFAULT 'en_revision',
            fecha_denuncia TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            anonimo BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        """)
        logger.info("✅ Tabla 'denuncias' creada/verificada")
        
        # 4. Tabla COMENTARIOS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS comentarios (
            id SERIAL PRIMARY KEY,
            reporte_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT DEFAULT 'comentario',
            FOREIGN KEY (reporte_id) REFERENCES reportes (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        """)
        logger.info("✅ Tabla 'comentarios' creada/verificada")
        
        # 5. Tabla SERVICIOS (CRÍTICA PARA LA PÁGINA /servicios)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS servicios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            icono TEXT,
            orden INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT TRUE
        )
        """)
        logger.info("✅ Tabla 'servicios' creada/verificada")
        
        # Insertar servicios por defecto si la tabla está vacía
        cur.execute("SELECT COUNT(*) FROM servicios")
        if cur.fetchone()[0] == 0:
            servicios = [
                ('Recolección de Desechos Sólidos', 'Servicio municipal de recolección de residuos sólidos. Horarios: Lunes, Miércoles, Viernes (6:00 AM - 2:00 PM)', 'fa-trash-alt', 1),
                ('Control de Maleza', 'Mantenimiento y limpieza de maleza en espacios públicos del distrito. Horarios: Lunes a Viernes (7:00 AM - 3:00 PM)', 'fa-leaf', 2),
                ('Atención Ciudadana', 'Servicio de atención y orientación a los ciudadanos. Horarios: Lunes a Viernes (8:00 AM - 4:00 PM)', 'fa-users', 3),
                ('Pago de Arbitrios', 'Puntos de recepción de pagos de arbitrios autorizados. Horarios: Lunes a Viernes (8:00 AM - 4:00 PM)', 'fa-file-invoice-dollar', 4),
                ('Supervisión de Construcciones', 'Recepción de denuncias y coordinación para construcciones irregulares. Horarios: Lunes a Viernes (8:00 AM - 4:00 PM)', 'fa-hard-hat', 5),
                ('Limpieza de Solares Baldíos', 'Gestión de limpieza de solares que representan riesgo sanitario. Horarios: Según programación semanal', 'fa-broom', 6)
            ]
            for servicio in servicios:
                cur.execute(
                    "INSERT INTO servicios (nombre, descripcion, icono, orden) VALUES (%s, %s, %s, %s)",
                    servicio
                )
            logger.info("✅ 6 servicios por defecto insertados")
        else:
            cur.execute("SELECT COUNT(*) FROM servicios")
            count = cur.fetchone()[0]
            logger.info(f"✅ Tabla 'servicios' ya tiene {count} registros")
        
        # 6. Tabla PROYECTOS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            imagen TEXT,
            fecha_inicio DATE,
            fecha_fin DATE,
            estado TEXT DEFAULT 'en_progreso',
            presupuesto REAL,
            porcentaje_completado INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT TRUE
        )
        """)
        logger.info("✅ Tabla 'proyectos' creada/verificada")
        
        # 7. Tabla AVISOS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS avisos (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            contenido TEXT NOT NULL,
            tipo TEXT DEFAULT 'general',
            fecha_publicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_expiracion DATE,
            importante BOOLEAN DEFAULT FALSE,
            activo BOOLEAN DEFAULT TRUE
        )
        """)
        logger.info("✅ Tabla 'avisos' creada/verificada")
        
        # 8. Tabla RESET_TOKENS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reset_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expiracion TIMESTAMP NOT NULL,
            usado BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES usuarios (id)
        )
        """)
        logger.info("✅ Tabla 'reset_tokens' creada/verificada")
        
        # 9. Tabla CONTACTOS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS contactos (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            telefono TEXT,
            asunto TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            estado TEXT DEFAULT 'nuevo',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            respuesta TEXT
        )
        """)
        logger.info("✅ Tabla 'contactos' creada/verificada")
        
        # 10. Crear usuario ADMIN si no existe
        admin_password = generate_password_hash('admin123')
        
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (ADMIN_EMAIL,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, rol_id) VALUES (%s, %s, %s, %s)",
                ('Administrador', ADMIN_EMAIL, admin_password, 1)
            )
            logger.info("✅ Usuario admin creado")
        else:
            logger.info("✅ Usuario admin ya existe")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("🎉 Base de datos PostgreSQL inicializada correctamente en Render")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al inicializar PostgreSQL en Render: {e}")
        return False

# ===============================
# DECORADORES Y HELPERS
# ===============================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión para acceder a esta página', 'warning')
            session['next_url'] = request.url
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Acceso denegado. Debe iniciar sesión', 'error')
            return redirect('/login')
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'SELECT rol_id FROM usuarios WHERE id = %s',
            (session['user_id'],)
        )
        usuario = cur.fetchone()
        conn.close()
        
        if not usuario or usuario[0] != 1:
            flash('Acceso denegado. Se requieren permisos de administrador', 'error')
            return redirect('/')
        
        return f(*args, **kwargs)
    return decorated_function

def get_user_role():
    if 'user_id' in session:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'SELECT rol_id FROM usuarios WHERE id = %s',
            (session['user_id'],)
        )
        usuario = cur.fetchone()
        conn.close()
        return usuario[0] if usuario else 2
    return 2

# ===============================
# RUTAS PRINCIPALES
# ===============================

@app.route("/")
@app.route("/index")
def index():
    """Página principal"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Obtener servicios
        try:
            cur.execute(
                'SELECT * FROM servicios WHERE activo = TRUE ORDER BY orden LIMIT 6'
            )
            servicios = dict_fetchall(cur)
            logger.info(f"✅ Index: {len(servicios)} servicios cargados")
        except Exception as e:
            logger.error(f"❌ Index - Error cargando servicios: {e}")
            servicios = []
        
        # Obtener avisos importantes
        try:
            cur.execute(
                '''SELECT * FROM avisos 
                   WHERE importante = TRUE AND activo = TRUE 
                   AND (fecha_expiracion IS NULL OR fecha_expiracion >= CURRENT_DATE)
                   ORDER BY fecha_publicacion DESC LIMIT 3'''
            )
            avisos = dict_fetchall(cur)
        except:
            avisos = []
        
        # Obtener proyectos activos
        try:
            cur.execute(
                'SELECT * FROM proyectos WHERE activo = TRUE ORDER BY fecha_inicio DESC LIMIT 3'
            )
            proyectos = dict_fetchall(cur)
        except:
            proyectos = []
        
        # Obtener estadísticas
        stats = {}
        try:
            cur.execute('SELECT COUNT(*) FROM usuarios')
            stats['total_usuarios'] = cur.fetchone()[0]
        except:
            stats['total_usuarios'] = 0
            
        try:
            cur.execute('SELECT COUNT(*) FROM reportes')
            stats['total_reportes'] = cur.fetchone()[0]
        except:
            stats['total_reportes'] = 0
            
        try:
            cur.execute("SELECT COUNT(*) FROM reportes WHERE estado = 'resuelto'")
            stats['reportes_resueltos'] = cur.fetchone()[0]
        except:
            stats['reportes_resueltos'] = 0
            
        try:
            cur.execute("SELECT COUNT(*) FROM proyectos WHERE estado = 'en_progreso'")
            stats['proyectos_activos'] = cur.fetchone()[0]
        except:
            stats['proyectos_activos'] = 0
        
        conn.close()
        
        return render_template("index.html", 
                             servicios=servicios, 
                             avisos=avisos,
                             proyectos=proyectos,
                             stats=stats)
    except Exception as e:
        logger.error(f"❌ Error en index: {e}")
        return render_template("index.html", servicios=[], avisos=[], proyectos=[], stats={})

# ===============================
# RUTA SERVICIOS - VERSIÓN CORREGIDA PARA RENDER
# ===============================

@app.route("/servicios")
def servicios():
    """Página de servicios - VERSIÓN MEJORADA PARA RENDER"""
    logger.info("🔍 Accediendo a /servicios")
    
    servicios_data = []
    error_db = None
    
    try:
        # Intento 1: Cargar desde PostgreSQL
        conn = get_db()
        cur = conn.cursor()
        
        # Verificar si la tabla servicios existe
        try:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'servicios'
                )
            """)
            tabla_existe = cur.fetchone()[0]
            
            if tabla_existe:
                cur.execute(
                    'SELECT id, nombre, descripcion, icono, orden FROM servicios WHERE activo = TRUE ORDER BY orden'
                )
                servicios_data = dict_fetchall(cur)
                logger.info(f"✅ {len(servicios_data)} servicios cargados desde PostgreSQL")
            else:
                logger.warning("⚠️ Tabla 'servicios' no existe en PostgreSQL")
                servicios_data = []
                
        except Exception as e:
            error_db = str(e)
            logger.error(f"❌ Error consultando servicios: {error_db}")
            servicios_data = []
            
        conn.close()
        
    except Exception as e:
        error_db = str(e)
        logger.error(f"❌ Error conexión PostgreSQL: {error_db}")
        servicios_data = []
    
    # Si no hay datos de PostgreSQL, usar datos de ejemplo
    if not servicios_data:
        servicios_data = [
            {
                'id': 1,
                'nombre': 'Recolección de Desechos Sólidos',
                'descripcion': 'Servicio de recolección programada en coordinación con el departamento municipal de aseo urbano. Horarios: Lunes, Miércoles y Viernes (6:00 AM - 2:00 PM)',
                'icono': 'fa-trash-alt',
                'orden': 1
            },
            {
                'id': 2,
                'nombre': 'Control de Maleza en Áreas Públicas',
                'descripcion': 'Mantenimiento y limpieza de maleza en espacios públicos del distrito. Horarios: Lunes a Viernes (7:00 AM - 3:00 PM)',
                'icono': 'fa-leaf',
                'orden': 2
            },
            {
                'id': 3,
                'nombre': 'Atención Ciudadana',
                'descripcion': 'Punto de atención general para trámites y consultas del distrito. Horarios: Lunes a Viernes (8:00 AM - 4:00 PM)',
                'icono': 'fa-users',
                'orden': 3
            },
            {
                'id': 4,
                'nombre': 'Pago de Arbitrios Distritales',
                'descripcion': 'Puntos de recepción de pagos de arbitrios autorizados por el municipio cabecera. Horarios: Lunes a Viernes (8:00 AM - 4:00 PM)',
                'icono': 'fa-file-invoice-dollar',
                'orden': 4
            }
        ]
        logger.info(f"✅ Usando {len(servicios_data)} servicios de ejemplo")
    
    # Renderizar la página
    try:
        return render_template("servicios.html", servicios=servicios_data)
    except Exception as e:
        logger.error(f"❌ Error renderizando servicios.html: {e}")
        # Fallback: página mínima
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Servicios - Ayuntamiento Cutupú</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                h1 {{ color: #1e3a8a; }}
                .servicio {{ background: white; padding: 20px; margin: 15px 0; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <h1>Servicios Municipales de Cutupú</h1>
            <p>Hay {len(servicios_data)} servicios disponibles:</p>
            
            {' '.join([f'<div class="servicio"><h3>{s["nombre"]}</h3><p>{s["descripcion"][:150]}...</p></div>' for s in servicios_data])}
            
            <p><a href="/">← Volver al inicio</a></p>
            <p><small>Error: {error_db if error_db else 'None'}</small></p>
        </body>
        </html>
        """

# ===============================
# RUTAS DE DIAGNÓSTICO PARA RENDER
# ===============================

@app.route("/health")
def health_check():
    """Verificar salud de la aplicación en Render"""
    try:
        # Probar PostgreSQL
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        
        # Verificar tabla servicios
        cur.execute("SELECT COUNT(*) FROM servicios")
        servicios_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"
        servicios_count = 0
    
    return jsonify({
        "status": "healthy",
        "service": "Ayuntamiento de Cutupú",
        "database": db_status,
        "servicios_count": servicios_count,
        "timestamp": datetime.now().isoformat(),
        "environment": "Render"
    })

@app.route("/debug/db")
def debug_database():
    """Página de debug para PostgreSQL en Render"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Información básica
        cur.execute("SELECT version(), current_database(), current_user, now()")
        db_info = cur.fetchone()
        
        # Tablas existentes
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        # Verificar tabla servicios específicamente
        servicios_existe = 'servicios' in tables
        servicios_count = 0
        servicios_ejemplo = []
        
        if servicios_existe:
            cur.execute("SELECT COUNT(*) FROM servicios")
            servicios_count = cur.fetchone()[0]
            
            cur.execute("SELECT id, nombre, descripcion FROM servicios LIMIT 5")
            servicios_ejemplo = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Página de debug HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug PostgreSQL - Render</title>
            <style>
                body {{ font-family: Arial; padding: 20px; }}
                .success {{ color: green; font-weight: bold; }}
                .error {{ color: red; font-weight: bold; }}
                .info {{ background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #1e3a8a; color: white; }}
            </style>
        </head>
        <body>
            <h1>🔍 Diagnóstico PostgreSQL - Render</h1>
            
            <div class="info">
                <h2>Información de Conexión</h2>
                <p><strong>PostgreSQL:</strong> {db_info[0]}</p>
                <p><strong>Base de datos:</strong> {db_info[1]}</p>
                <p><strong>Usuario:</strong> {db_info[2]}</p>
                <p><strong>Hora servidor:</strong> {db_info[3]}</p>
                <p><strong>URL:</strong> {DATABASE_URL[:30]}...</p>
            </div>
            
            <div class="info">
                <h2>Tablas en la Base de Datos</h2>
                {f'<p>Total: {len(tables)} tablas</p><ul>' + ''.join([f'<li>{table}</li>' for table in tables]) + '</ul>' if tables else '<p class="error">No hay tablas en la base de datos</p>'}
            </div>
            
            <div class="info">
                <h2>Tabla 'servicios'</h2>
                {f'<p class="success">✅ La tabla "servicios" EXISTE</p><p><strong>Total de servicios:</strong> {servicios_count}</p>' + 
                 (f'<h3>Primeros 5 servicios:</h3><table><tr><th>ID</th><th>Nombre</th><th>Descripción</th></tr>' + 
                  ''.join([f'<tr><td>{s[0]}</td><td>{s[1]}</td><td>{s[2][:50]}...</td></tr>' for s in servicios_ejemplo]) + 
                  '</table>' if servicios_ejemplo else '') if servicios_existe else 
                 '<p class="error">❌ La tabla "servicios" NO existe</p><p>La aplicación la creará automáticamente.</p>'}
            </div>
            
            <div class="info">
                <h2>Enlaces de Prueba</h2>
                <ul>
                    <li><a href="/health">Health Check</a></li>
                    <li><a href="/servicios">Página de Servicios</a></li>
                    <li><a href="/">Inicio</a></li>
                </ul>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Error de Base de Datos</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>URL:</strong> {DATABASE_URL[:50]}...</p>
            <p><strong>Solución Render:</strong> Asegúrate de usar SSL en la conexión (sslmode='require')</p>
        </body>
        </html>
        """, 500

# ===============================
# [EL RESTO DE TU CÓDIGO PERMANECE IGUAL - login, perfil, reportes, etc.]
# ===============================

# [MANTÉN TODAS LAS OTRAS FUNCIONES COMO ESTÁN EN TU ARCHIVO ORIGINAL]
# Solo cambia la función get_db() y servicios() como arriba

# ... [TODO EL RESTO DE TU CÓDIGO IGUAL] ...

@app.route("/servicio/<int:id>")
def servicio_detalle(id):
    """Detalle de un servicio específico"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM servicios WHERE id = %s AND activo = TRUE',
            (id,)
        )
        servicio = dict_fetchone(cur)
        conn.close()
        
        if servicio:
            return render_template("servicio_detalle.html", servicio=servicio)
        else:
            flash('Servicio no encontrado', 'error')
            return redirect('/servicios')
    except Exception as e:
        logger.error(f"⚠️ Error en servicio_detalle: {e}")
        flash('Error al cargar el servicio', 'error')
        return redirect('/servicios')

# ===============================
# INICIALIZAR BASE DE DATOS AL ARRANCAR
# ===============================
with app.app_context():
    verificar_y_preparar_db()

# ===============================
# INICIALIZACIÓN Y EJECUCIÓN
# ===============================

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("🚀 SISTEMA AYUNTAMIENTO DE CUTUPÚ - VERSIÓN RENDER (PostgreSQL con SSL)")
    print("="*60)
    
    # Crear carpeta de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(f"📁 Carpeta de uploads creada: {app.config['UPLOAD_FOLDER']}")
    
    print(f"\n🔑 INFORMACIÓN DE ACCESO:")
    print(f"   1. Para ADMIN:")
    print(f"      Email: {ADMIN_EMAIL}")
    print(f"      Contraseña: admin123")
    print(f"   2. También puedes registrar una cuenta nueva")
    print("="*60)
    
    print("\n✅ Sistema PostgreSQL listo para ejecutar en Render")
    print("🌐 URLs de prueba:")
    print("   - Health Check: http://localhost:5000/health")
    print("   - Debug DB: http://localhost:5000/debug/db")
    print("   - Servicios: http://localhost:5000/servicios")
    print("="*60)

    # ARRANCAR SERVIDOR FLASK
    app.run(debug=True, host="0.0.0.0", port=5000)