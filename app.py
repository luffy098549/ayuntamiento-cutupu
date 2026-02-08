from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
import random
import string
import json
import csv
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'cutupu-secret-key-123'
app.config['DATABASE'] = 'cutupu.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

# ===============================
# CONFIGURACIÓN BASADA EN LA BD REAL
# ===============================

ADMIN_EMAIL = 'admin@ayuntamiento.gob'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db():
    """Conectar a la base de datos existente"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializar la base de datos adaptándose a la estructura existente"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar y crear tablas faltantes basadas en las que ya tienes
        tablas_existentes = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tablas_nombres = [t[0] for t in tablas_existentes]
        
        # Tabla usuarios si no existe
        if 'usuarios' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    telefono TEXT,
                    direccion TEXT,
                    cedula TEXT,
                    rol_id INTEGER DEFAULT 2,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activo BOOLEAN DEFAULT 1
                )
            ''')
            print("✅ Tabla 'usuarios' creada")
        
        # Si existe tabla usuarios pero no tiene creado_en, agregarlo
        elif 'usuarios' in tablas_nombres:
            cursor.execute("PRAGMA table_info(usuarios)")
            columnas = [col[1] for col in cursor.fetchall()]
            if 'creado_en' not in columnas:
                cursor.execute('ALTER TABLE usuarios ADD COLUMN creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                print("✅ Columna 'creado_en' agregada a tabla 'usuarios'")
        
        # Tabla reportes si no existe
        if 'reportes' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE reportes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            ''')
            print("✅ Tabla 'reportes' creada")
        
        # Tabla denuncias si no existe
        if 'denuncias' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE denuncias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    anonimo BOOLEAN DEFAULT 0,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')
            print("✅ Tabla 'denuncias' creada")
        
        # Tabla comentarios si no existe
        if 'comentarios' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE comentarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporte_id INTEGER NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    contenido TEXT NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tipo TEXT DEFAULT 'comentario',
                    FOREIGN KEY (reporte_id) REFERENCES reportes (id),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')
            print("✅ Tabla 'comentarios' creada")
        
        # Si no existe tabla servicios, crearla con estructura completa
        if 'servicios' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE servicios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    icono TEXT,
                    orden INTEGER DEFAULT 0,
                    activo BOOLEAN DEFAULT 1
                )
            ''')
            print("✅ Tabla 'servicios' creada")
            
            # Insertar servicios de ejemplo
            servicios_ejemplo = [
                ('Atención Ciudadana', 'Servicio de atención y orientación a los ciudadanos', 'fa-users', 1),
                ('Gestión de Trámites', 'Procesamiento de documentos y certificados', 'fa-file-alt', 2),
                ('Denuncias y Reportes', 'Sistema de denuncias y reportes ciudadanos', 'fa-exclamation-triangle', 3),
                ('Proyectos Municipales', 'Información sobre proyectos en ejecución', 'fa-project-diagram', 4),
                ('Transparencia', 'Acceso a información pública municipal', 'fa-chart-line', 5)
            ]
            
            for servicio in servicios_ejemplo:
                cursor.execute('''
                    INSERT INTO servicios (nombre, descripcion, icono, orden) VALUES (?, ?, ?, ?)
                ''', servicio)
        
        # Si no existe tabla proyectos, crearla con estructura completa
        if 'proyectos' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    imagen TEXT,
                    fecha_inicio DATE,
                    fecha_fin DATE,
                    estado TEXT DEFAULT 'en_progreso',
                    presupuesto REAL,
                    porcentaje_completado INTEGER DEFAULT 0,
                    activo BOOLEAN DEFAULT 1
                )
            ''')
            print("✅ Tabla 'proyectos' creada")
        
        # Si no existe tabla avisos, crearla con estructura completa
        if 'avisos' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE avisos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    tipo TEXT DEFAULT 'general',
                    fecha_publicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_expiracion DATE,
                    importante BOOLEAN DEFAULT 0,
                    activo BOOLEAN DEFAULT 1
                )
            ''')
            print("✅ Tabla 'avisos' creada")
        
        # Tabla reset_tokens si no existe
        if 'reset_tokens' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expiracion TIMESTAMP NOT NULL,
                    usado BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES usuarios (id)
                )
            ''')
            print("✅ Tabla 'reset_tokens' creada")
        
        # Tabla contactos si no existe
        if 'contactos' not in tablas_nombres:
            cursor.execute('''
                CREATE TABLE contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    email TEXT NOT NULL,
                    telefono TEXT,
                    asunto TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    estado TEXT DEFAULT 'nuevo',
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    respuesta TEXT
                )
            ''')
            print("✅ Tabla 'contactos' creada")
        
        # Insertar usuario admin si no existe
        admin_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT OR IGNORE INTO usuarios (nombre, email, password_hash, rol_id, creado_en)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ('Administrador', ADMIN_EMAIL, admin_hash, 1))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en init_db: {e}")
        return False

def verificar_y_preparar_db():
    """Verificar y preparar la base de datos con la estructura REAL"""
    try:
        if not init_db():
            return False
        
        conn = get_db()
        
        # Verificar tablas
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas_existentes = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Base de datos verificada: {app.config['DATABASE']}")
        print(f"📊 Tablas encontradas: {', '.join(tablas_existentes)}")
        
        # Verificar estructura de tabla usuarios
        cursor = conn.execute("PRAGMA table_info(usuarios)")
        columnas_info = cursor.fetchall()
        
        print("\n🔍 Estructura de tabla 'usuarios':")
        for col in columnas_info:
            print(f"   {col[1]} ({col[2]})")
        
        # Verificar usuario admin
        admin = conn.execute(
            'SELECT id, nombre, email, password_hash FROM usuarios WHERE email = ?',
            (ADMIN_EMAIL,)
        ).fetchone()
        
        if admin:
            print(f"\n👤 Usuario admin encontrado:")
            print(f"   ID: {admin['id']}")
            print(f"   Nombre: {admin['nombre']}")
            print(f"   Email: {admin['email']}")
        else:
            print(f"\n⚠️  Usuario admin no encontrado, creando...")
            admin_hash = generate_password_hash('admin123')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO usuarios (nombre, email, password_hash, rol_id, creado_en) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
                ('Administrador', ADMIN_EMAIL, admin_hash, 1)
            )
            conn.commit()
            print(f"✅ Usuario admin creado")
        
        # Contar registros
        total_usuarios = conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
        
        # Verificar si existen otras tablas importantes y contar registros
        for tabla in ['reportes', 'denuncias', 'servicios', 'proyectos', 'avisos']:
            if tabla in tablas_existentes:
                count = conn.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]
                print(f"   📊 {tabla.capitalize()}: {count}")
            else:
                print(f"   📊 {tabla.capitalize()}: Tabla no existe")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error al verificar base de datos: {e}")
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
        usuario = conn.execute(
            'SELECT rol_id FROM usuarios WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        conn.close()
        
        if not usuario or usuario['rol_id'] != 1:
            flash('Acceso denegado. Se requieren permisos de administrador', 'error')
            return redirect('/')
        
        return f(*args, **kwargs)
    return decorated_function

def get_user_role():
    if 'user_id' in session:
        conn = get_db()
        usuario = conn.execute(
            'SELECT rol_id FROM usuarios WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        conn.close()
        return usuario['rol_id'] if usuario else 2
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
        
        # Obtener servicios
        try:
            servicios = conn.execute(
                'SELECT * FROM servicios WHERE activo = 1 ORDER BY orden LIMIT 6'
            ).fetchall()
        except:
            servicios = []
        
        # Obtener avisos importantes
        try:
            avisos = conn.execute(
                '''SELECT * FROM avisos 
                   WHERE importante = 1 AND activo = 1 
                   AND (fecha_expiracion IS NULL OR fecha_expiracion >= DATE('now'))
                   ORDER BY fecha_publicacion DESC LIMIT 3'''
            ).fetchall()
        except:
            avisos = []
        
        # Obtener proyectos activos
        try:
            proyectos = conn.execute(
                'SELECT * FROM proyectos WHERE activo = 1 ORDER BY fecha_inicio DESC LIMIT 3'
            ).fetchall()
        except:
            proyectos = []
        
        # Obtener estadísticas
        stats = {}
        try:
            stats['total_reportes'] = conn.execute('SELECT COUNT(*) FROM reportes').fetchone()[0]
            stats['reportes_resueltos'] = conn.execute("SELECT COUNT(*) FROM reportes WHERE estado = 'resuelto'").fetchone()[0]
        except:
            stats['total_reportes'] = 0
            stats['reportes_resueltos'] = 0
            
        try:
            stats['proyectos_activos'] = conn.execute("SELECT COUNT(*) FROM proyectos WHERE estado = 'en_progreso'").fetchone()[0]
        except:
            stats['proyectos_activos'] = 0
        
        conn.close()
        
        return render_template("index.html", 
                             servicios=servicios, 
                             avisos=avisos,
                             proyectos=proyectos,
                             stats=stats)
    except Exception as e:
        print(f"⚠️ Error en index: {e}")
        return render_template("index.html", servicios=[], avisos=[], proyectos=[], stats={})

@app.route("/login", methods=["GET", "POST"])
def login():
    """Página de inicio de sesión - MANEJA TANTO LOGIN COMO REGISTRO"""
    if 'user_id' in session:
        flash('Ya tienes una sesión activa', 'info')
        return redirect('/')
    
    # Determinar si estamos en modo registro
    register = request.args.get('register') == 'true'
    
    if request.method == "POST":
        # Si es una solicitud POST, determinar si es login o registro
        # Por el campo 'nombre' podemos saber si es registro
        if 'nombre' in request.form:
            # ========== ES UN REGISTRO ==========
            nombre = request.form.get("nombre", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            telefono = request.form.get("telefono", "").strip()
            cedula = request.form.get("cedula", "").strip()
            
            if not nombre or not email or not password:
                flash('Todos los campos son obligatorios', 'error')
                return render_template("login.html", register=True)
            
            if len(password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres', 'error')
                return render_template("login.html", register=True)
            
            if password != confirm_password:
                flash('Las contraseñas no coinciden', 'error')
                return render_template("login.html", register=True)
            
            try:
                conn = get_db()
                
                # Verificar si el email ya existe
                existe = conn.execute(
                    'SELECT id FROM usuarios WHERE email = ?',
                    (email,)
                ).fetchone()
                
                if existe:
                    flash('Este correo electrónico ya está registrado', 'error')
                    conn.close()
                    return render_template("login.html", register=True)
                
                # Crear nuevo usuario
                password_hash = generate_password_hash(password)
                
                conn.execute(
                    '''INSERT INTO usuarios (nombre, email, password_hash, telefono, cedula, rol_id, creado_en)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                    (nombre, email, password_hash, telefono, cedula, 2)
                )
                
                conn.commit()
                conn.close()
                
                flash('¡Registro exitoso! Ahora puede iniciar sesión', 'success')
                return redirect('/login?registro=ok')
                
            except Exception as e:
                print(f"🔥 Error en registro: {str(e)}")
                flash(f'Error al registrar usuario: {str(e)}', 'error')
                return render_template("login.html", register=True)
        
        else:
            # ========== ES UN LOGIN ==========
            email = request.form.get("usuario", "").strip().lower()
            password = request.form.get("password", "")
            remember = request.form.get("remember")
            
            if not email or not password:
                flash('Por favor complete todos los campos', 'error')
                return render_template("login.html", register=False)
            
            try:
                conn = get_db()
                query = 'SELECT id, nombre, email, password_hash, rol_id FROM usuarios WHERE email = ?'
                usuario = conn.execute(query, (email,)).fetchone()
                conn.close()
                
                if usuario:
                    # Acceder correctamente a la columna password_hash
                    password_hash = usuario['password_hash']
                    
                    if check_password_hash(password_hash, password):
                        session['user_id'] = usuario['id']
                        session['user_name'] = usuario['nombre']
                        session['user_email'] = usuario['email']
                        session['user_role'] = usuario['rol_id']
                        
                        if remember:
                            session.permanent = True
                        
                        flash(f'¡Bienvenido/a {usuario["nombre"]}!', 'success')
                        
                        next_url = session.pop('next_url', None)
                        if next_url:
                            return redirect(next_url)
                        
                        if session['user_role'] == 1:
                            return redirect('/admin')
                        
                        return redirect('/')
                    else:
                        flash('Correo o contraseña incorrectos', 'error')
                else:
                    flash('Correo o contraseña incorrectos', 'error')
                    
            except Exception as e:
                print(f"🔥 Error en login: {str(e)}")
                flash(f'Error al iniciar sesión: {str(e)}', 'error')
        
        return render_template("login.html", register=register)
    
    # Si es GET request, mostrar formulario apropiado
    registro_ok = request.args.get('registro')
    if registro_ok == 'ok':
        flash('¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.', 'success')
    
    return render_template("login.html", register=register)

@app.route("/register")
def register_redirect():
    """Redirigir al formulario de registro"""
    return redirect(url_for('login', register='true'))

@app.route("/olvido-contrasena", methods=["GET", "POST"])
def olvido_contrasena():
    """Página para recuperar contraseña"""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        
        if not email:
            flash('Por favor ingrese su correo electrónico', 'error')
            return render_template("olvido_contrasena.html")
        
        try:
            conn = get_db()
            usuario = conn.execute(
                'SELECT id, nombre FROM usuarios WHERE email = ?',
                (email,)
            ).fetchone()
            
            if usuario:
                # Generar token único
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                expiracion = datetime.now() + timedelta(hours=24)
                
                conn.execute(
                    'INSERT INTO reset_tokens (user_id, token, expiracion) VALUES (?, ?, ?)',
                    (usuario['id'], token, expiracion)
                )
                
                conn.commit()
                conn.close()
                
                # En un entorno real, aquí enviarías el email
                reset_url = url_for('restablecer_contrasena', token=token, _external=True)
                flash(f'Se ha enviado un enlace de recuperación a {email}', 'info')
                flash(f'Enlace de prueba: {reset_url}', 'info')
            else:
                flash('No se encontró una cuenta con ese correo electrónico', 'error')
                conn.close()
            
        except Exception as e:
            print(f"❌ Error en olvido-contrasena: {str(e)}")
            flash('Error al procesar la solicitud', 'error')
        
        return render_template("olvido_contrasena.html")
    
    return render_template("olvido_contrasena.html")

@app.route("/restablecer-contrasena/<token>", methods=["GET", "POST"])
def restablecer_contrasena(token=None):
    """Restablecer contraseña con token"""
    if not token and request.method == "GET":
        token = request.args.get('token')
    
    if not token:
        flash('Token no válido', 'error')
        return redirect('/olvido-contrasena')
    
    try:
        conn = get_db()
        
        # Verificar token válido
        token_data = conn.execute(
            '''SELECT * FROM reset_tokens 
               WHERE token = ? AND usado = 0 AND expiracion > datetime('now')''',
            (token,)
        ).fetchone()
        
        if not token_data:
            flash('Token inválido o expirado', 'error')
            conn.close()
            return redirect('/olvido-contrasena')
        
        if request.method == "POST":
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            
            if not password or not confirm_password:
                flash('Por favor complete todos los campos', 'error')
                return render_template("restablecer_contrasena.html", token=token, valid=True)
            
            if len(password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres', 'error')
                return render_template("restablecer_contrasena.html", token=token, valid=True)
            
            if password != confirm_password:
                flash('Las contraseñas no coinciden', 'error')
                return render_template("restablecer_contrasena.html", token=token, valid=True)
            
            # Actualizar contraseña
            password_hash = generate_password_hash(password)
            conn.execute(
                'UPDATE usuarios SET password_hash = ? WHERE id = ?',
                (password_hash, token_data['user_id'])
            )
            
            # Marcar token como usado
            conn.execute(
                'UPDATE reset_tokens SET usado = 1 WHERE id = ?',
                (token_data['id'],)
            )
            
            conn.commit()
            conn.close()
            
            flash('Contraseña restablecida exitosamente. Ahora puede iniciar sesión.', 'success')
            return redirect('/login')
        
        conn.close()
        return render_template("restablecer_contrasena.html", token=token, valid=True)
        
    except Exception as e:
        print(f"❌ Error en restablecer-contrasena: {str(e)}")
        flash('Error al procesar la solicitud', 'error')
        return redirect('/olvido-contrasena')

@app.route("/logout")
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect('/')

# ===============================
# RUTAS DEL PERFIL DE USUARIO
# ===============================

@app.route("/perfil")
@login_required
def perfil():
    """Perfil del usuario"""
    try:
        conn = get_db()
        
        # Obtener datos del usuario - USAR creado_en
        usuario_db = conn.execute(
            '''SELECT id, nombre, email, telefono, direccion, cedula, 
                      creado_en, rol_id 
               FROM usuarios WHERE id = ?''',
            (session['user_id'],)
        ).fetchone()
        
        if not usuario_db:
            flash('Usuario no encontrado', 'error')
            conn.close()
            return redirect('/')
        
        # Obtener estadísticas del usuario
        total_reportes = 0
        total_denuncias = 0
        reportes_resueltos = 0
        
        try:
            total_reportes = conn.execute(
                'SELECT COUNT(*) FROM reportes WHERE usuario_id = ?',
                (session['user_id'],)
            ).fetchone()[0]
        except:
            pass
        
        try:
            total_denuncias = conn.execute(
                'SELECT COUNT(*) FROM denuncias WHERE usuario_id = ?',
                (session['user_id'],)
            ).fetchone()[0]
        except:
            pass
        
        try:
            reportes_resueltos = conn.execute(
                "SELECT COUNT(*) FROM reportes WHERE usuario_id = ? AND estado = 'resuelto'",
                (session['user_id'],)
            ).fetchone()[0]
        except:
            pass
        
        # Obtener últimos reportes
        ultimos_reportes = []
        try:
            ultimos_reportes = conn.execute(
                '''SELECT * FROM reportes 
                   WHERE usuario_id = ? 
                   ORDER BY fecha_reporte DESC LIMIT 5''',
                (session['user_id'],)
            ).fetchall()
        except:
            pass
        
        conn.close()
        
        usuario = dict(usuario_db)
        # Usar creado_en en lugar de fecha_registro
        if 'creado_en' in usuario and usuario['creado_en']:
            try:
                usuario['fecha_registro'] = datetime.strptime(usuario['creado_en'], '%Y-%m-%d %H:%M:%S')
            except:
                usuario['fecha_registro'] = usuario['creado_en']
        else:
            usuario['fecha_registro'] = datetime.now()
        
        return render_template("perfil.html", 
                             usuario=usuario,
                             total_reportes=total_reportes,
                             total_denuncias=total_denuncias,
                             reportes_resueltos=reportes_resueltos,
                             ultimos_reportes=ultimos_reportes)
    except Exception as e:
        print(f"❌ Error en perfil: {str(e)}")
        flash('Error al cargar el perfil', 'error')
        return redirect('/')

@app.route("/actualizar-perfil", methods=["POST"])
@login_required
def actualizar_perfil():
    """Actualizar información del perfil del usuario"""
    try:
        nombre = request.form.get("nombre", "").strip()
        telefono = request.form.get("telefono", "").strip()
        direccion = request.form.get("direccion", "").strip()
        cedula = request.form.get("cedula", "").strip()
        
        if not nombre:
            flash('El nombre es obligatorio', 'error')
            return redirect('/perfil')
        
        conn = get_db()
        
        conn.execute(
            '''UPDATE usuarios SET nombre = ?, telefono = ?, 
               direccion = ?, cedula = ? WHERE id = ?''',
            (nombre, telefono, direccion, cedula, session['user_id'])
        )
        
        conn.commit()
        
        # Actualizar sesión
        session['user_name'] = nombre
        
        conn.close()
        
        flash('Perfil actualizado correctamente', 'success')
        
    except Exception as e:
        print(f"❌ Error en actualizar-perfil: {str(e)}")
        flash('Error al actualizar el perfil', 'error')
    
    return redirect('/perfil')

@app.route("/cambiar-contrasena", methods=["POST"])
@login_required
def cambiar_contrasena():
    """Cambiar contraseña del usuario"""
    try:
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son obligatorios', 'error')
            return redirect('/perfil')
        
        if new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden', 'error')
            return redirect('/perfil')
        
        if len(new_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'error')
            return redirect('/perfil')
        
        conn = get_db()
        usuario = conn.execute(
            'SELECT password_hash FROM usuarios WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            conn.close()
            return redirect('/perfil')
        
        # Verificar contraseña actual
        if not check_password_hash(usuario['password_hash'], current_password):
            flash('Contraseña actual incorrecta', 'error')
            conn.close()
            return redirect('/perfil')
        
        # Actualizar contraseña
        new_hash = generate_password_hash(new_password)
        conn.execute(
            'UPDATE usuarios SET password_hash = ? WHERE id = ?',
            (new_hash, session['user_id'])
        )
        conn.commit()
        conn.close()
        
        flash('Contraseña cambiada exitosamente', 'success')
        
    except Exception as e:
        print(f"❌ Error en cambiar-contrasena: {str(e)}")
        flash('Error al cambiar la contraseña', 'error')
    
    return redirect('/perfil')

# ===============================
# RUTAS DE REPORTES
# ===============================

@app.route("/reportar", methods=["GET", "POST"])
@login_required
def reportar():
    """Página para crear reportes"""
    if request.method == "POST":
        try:
            titulo = request.form.get("titulo", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            categoria = request.form.get("categoria", "").strip()
            ubicacion = request.form.get("ubicacion", "").strip()
            latitud = request.form.get("latitud", "")
            longitud = request.form.get("longitud", "")
            prioridad = request.form.get("prioridad", "media")
            
            if not titulo or not descripcion or not categoria or not ubicacion:
                flash('Todos los campos obligatorios deben ser completados', 'error')
                return render_template("reportar.html")
            
            # Manejar subida de imagen
            imagen = None
            if 'imagen' in request.files:
                file = request.files['imagen']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    imagen = filename
            
            conn = get_db()
            
            conn.execute(
                '''INSERT INTO reportes 
                   (usuario_id, titulo, descripcion, categoria, ubicacion, 
                    latitud, longitud, prioridad, imagen)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (session['user_id'], titulo, descripcion, categoria, ubicacion,
                 latitud if latitud else None, longitud if longitud else None,
                 prioridad, imagen)
            )
            
            conn.commit()
            conn.close()
            
            flash('Reporte enviado exitosamente. Será revisado por el personal correspondiente.', 'success')
            return redirect('/mis_reportes')
            
        except Exception as e:
            print(f"❌ Error en reportar: {str(e)}")
            flash('Error al enviar el reporte', 'error')
    
    return render_template("reportar.html")

@app.route("/mis_reportes")
@login_required
def mis_reportes():
    """Página para ver mis reportes"""
    try:
        conn = get_db()
        
        # Verificar si la tabla reportes existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reportes'")
        if not cursor.fetchone():
            conn.close()
            return render_template("mis_reportes.html", 
                                 reportes=[],
                                 categorias=[],
                                 total=0,
                                 pendientes=0,
                                 en_proceso=0,
                                 resueltos=0)
        
        # Obtener filtros
        estado_filter = request.args.get('estado', '')
        categoria_filter = request.args.get('categoria', '')
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        
        # Construir consulta
        query = '''SELECT * FROM reportes WHERE usuario_id = ?'''
        params = [session['user_id']]
        
        if estado_filter:
            query += ' AND estado = ?'
            params.append(estado_filter)
        
        if categoria_filter:
            query += ' AND categoria = ?'
            params.append(categoria_filter)
        
        if fecha_inicio:
            query += ' AND DATE(fecha_reporte) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(fecha_reporte) <= ?'
            params.append(fecha_fin)
        
        query += ' ORDER BY fecha_reporte DESC'
        
        reportes = conn.execute(query, params).fetchall()
        
        # Obtener categorías únicas para el filtro
        try:
            categorias = conn.execute(
                'SELECT DISTINCT categoria FROM reportes WHERE usuario_id = ? ORDER BY categoria',
                (session['user_id'],)
            ).fetchall()
        except:
            categorias = []
        
        # Obtener estadísticas
        total = len(reportes)
        pendientes = len([r for r in reportes if r['estado'] == 'pendiente'])
        en_proceso = len([r for r in reportes if r['estado'] == 'en_proceso'])
        resueltos = len([r for r in reportes if r['estado'] == 'resuelto'])
        
        conn.close()
        
        return render_template("mis_reportes.html", 
                             reportes=reportes,
                             categorias=categorias,
                             total=total,
                             pendientes=pendientes,
                             en_proceso=en_proceso,
                             resueltos=resueltos,
                             estado_filter=estado_filter,
                             categoria_filter=categoria_filter,
                             fecha_inicio=fecha_inicio,
                             fecha_fin=fecha_fin)
    except Exception as e:
        print(f"❌ Error en mis_reportes: {str(e)}")
        flash('Error al cargar los reportes', 'error')
        return redirect('/')

@app.route("/reporte/<int:id>")
@login_required
def ver_reporte(id):
    """Ver detalles de un reporte específico"""
    try:
        conn = get_db()
        
        # Obtener reporte
        reporte = conn.execute(
            'SELECT r.*, u.nombre as usuario_nombre FROM reportes r JOIN usuarios u ON r.usuario_id = u.id WHERE r.id = ?',
            (id,)
        ).fetchone()
        
        if not reporte:
            flash('Reporte no encontrado', 'error')
            conn.close()
            return redirect('/mis_reportes')
        
        # Verificar permisos
        if reporte['usuario_id'] != session['user_id'] and get_user_role() != 1:
            flash('No tiene permisos para ver este reporte', 'error')
            conn.close()
            return redirect('/mis_reportes')
        
        # Obtener comentarios
        comentarios = []
        try:
            comentarios = conn.execute(
                '''SELECT c.*, u.nombre as usuario_nombre 
                   FROM comentarios c 
                   JOIN usuarios u ON c.usuario_id = u.id 
                   WHERE c.reporte_id = ? 
                   ORDER BY c.fecha ASC''',
                (id,)
            ).fetchall()
        except:
            pass
        
        conn.close()
        
        return render_template("reporte_detalle.html", 
                             reporte=reporte, 
                             comentarios=comentarios)
    except Exception as e:
        print(f"❌ Error en ver_reporte: {str(e)}")
        flash('Error al cargar el reporte', 'error')
        return redirect('/mis_reportes')

@app.route("/reporte/<int:id>/comentar", methods=["POST"])
@login_required
def comentar_reporte(id):
    """Agregar comentario a un reporte"""
    try:
        contenido = request.form.get("comentario", "").strip()
        tipo = request.form.get("tipo", "comentario")
        
        if not contenido:
            flash('El comentario no puede estar vacío', 'error')
            return redirect(f'/reporte/{id}')
        
        conn = get_db()
        
        # Verificar que el reporte existe y el usuario tiene acceso
        reporte = conn.execute(
            'SELECT usuario_id FROM reportes WHERE id = ?',
            (id,)
        ).fetchone()
        
        if not reporte:
            flash('Reporte no encontrado', 'error')
            conn.close()
            return redirect('/mis_reportes')
        
        if reporte['usuario_id'] != session['user_id'] and get_user_role() != 1:
            flash('No tiene permisos para comentar en este reporte', 'error')
            conn.close()
            return redirect('/mis_reportes')
        
        # Insertar comentario
        conn.execute(
            '''INSERT INTO comentarios (reporte_id, usuario_id, contenido, tipo)
               VALUES (?, ?, ?, ?)''',
            (id, session['user_id'], contenido, tipo)
        )
        
        # Actualizar fecha de actualización del reporte
        conn.execute(
            'UPDATE reportes SET fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?',
            (id,)
        )
        
        conn.commit()
        conn.close()
        
        flash('Comentario agregado exitosamente', 'success')
        
    except Exception as e:
        print(f"❌ Error en comentar_reporte: {str(e)}")
        flash('Error al agregar comentario', 'error')
    
    return redirect(f'/reporte/{id}')

# ===============================
# RUTAS DE DENUNCIAS
# ===============================

@app.route("/denunciar", methods=["GET", "POST"])
@login_required
def denunciar():
    """Página para crear denuncias"""
    if request.method == "POST":
        try:
            titulo = request.form.get("titulo", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            tipo = request.form.get("tipo", "").strip()
            denunciado_nombre = request.form.get("denunciado_nombre", "").strip()
            denunciado_cargo = request.form.get("denunciado_cargo", "").strip()
            denunciado_institucion = request.form.get("denunciado_institucion", "").strip()
            pruebas = request.form.get("pruebas", "").strip()
            anonimo = 1 if request.form.get("anonimo") else 0
            
            if not titulo or not descripcion or not tipo:
                flash('Todos los campos obligatorios deben ser completados', 'error')
                return render_template("denunciar.html")
            
            conn = get_db()
            
            conn.execute(
                '''INSERT INTO denuncias 
                   (usuario_id, titulo, descripcion, tipo, denunciado_nombre,
                    denunciado_cargo, denunciado_institucion, pruebas, anonimo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (session['user_id'], titulo, descripcion, tipo, 
                 denunciado_nombre if denunciado_nombre else None,
                 denunciado_cargo if denunciado_cargo else None,
                 denunciado_institucion if denunciado_institucion else None,
                 pruebas if pruebas else None, anonimo)
            )
            
            conn.commit()
            conn.close()
            
            flash('Denuncia enviada exitosamente. Será revisada por el comité correspondiente.', 'success')
            return redirect('/mis_denuncias')
            
        except Exception as e:
            print(f"❌ Error en denunciar: {str(e)}")
            flash('Error al enviar la denuncia', 'error')
    
    return render_template("denunciar.html")

@app.route("/mis_denuncias")
@login_required
def mis_denuncias():
    """Página para ver mis denuncias"""
    try:
        conn = get_db()
        
        # Verificar si la tabla denuncias existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='denuncias'")
        if not cursor.fetchone():
            conn.close()
            return render_template("mis_denuncias.html", 
                                 denuncias=[],
                                 tipos=[],
                                 estado_filter='',
                                 tipo_filter='')
        
        # Obtener filtros
        estado_filter = request.args.get('estado', '')
        tipo_filter = request.args.get('tipo', '')
        
        # Construir consulta
        query = '''SELECT * FROM denuncias WHERE usuario_id = ?'''
        params = [session['user_id']]
        
        if estado_filter:
            query += ' AND estado = ?'
            params.append(estado_filter)
        
        if tipo_filter:
            query += ' AND tipo = ?'
            params.append(tipo_filter)
        
        query += ' ORDER BY fecha_denuncia DESC'
        
        denuncias = conn.execute(query, params).fetchall()
        
        # Obtener tipos únicos para el filtro
        try:
            tipos = conn.execute(
                'SELECT DISTINCT tipo FROM denuncias WHERE usuario_id = ? ORDER BY tipo',
                (session['user_id'],)
            ).fetchall()
        except:
            tipos = []
        
        conn.close()
        
        return render_template("mis_denuncias.html", 
                             denuncias=denuncias,
                             tipos=tipos,
                             estado_filter=estado_filter,
                             tipo_filter=tipo_filter)
    except Exception as e:
        print(f"❌ Error en mis_denuncias: {str(e)}")
        flash('Error al cargar las denuncias', 'error')
        return redirect('/')

@app.route("/denuncia/<int:id>")
@login_required
def ver_denuncia(id):
    """Ver detalles de una denuncia específica"""
    try:
        conn = get_db()
        
        # Obtener denuncia
        denuncia = conn.execute(
            'SELECT d.*, u.nombre as usuario_nombre FROM denuncias d JOIN usuarios u ON d.usuario_id = u.id WHERE d.id = ?',
            (id,)
        ).fetchone()
        
        if not denuncia:
            flash('Denuncia no encontrada', 'error')
            conn.close()
            return redirect('/mis_denuncias')
        
        # Verificar permisos
        if denuncia['usuario_id'] != session['user_id'] and get_user_role() != 1:
            flash('No tiene permisos para ver esta denuncia', 'error')
            conn.close()
            return redirect('/mis_denuncias')
        
        conn.close()
        
        return render_template("denuncia_detalle.html", denuncia=denuncia)
    except Exception as e:
        print(f"❌ Error en ver_denuncia: {str(e)}")
        flash('Error al cargar la denuncia', 'error')
        return redirect('/mis_denuncias')

# ===============================
# RUTAS DE SERVICIOS
# ===============================

@app.route("/servicios")
def servicios():
    """Página de servicios"""
    try:
        conn = get_db()
        try:
            servicios = conn.execute(
                'SELECT * FROM servicios WHERE activo = 1 ORDER BY orden'
            ).fetchall()
        except:
            servicios = []
        conn.close()
        return render_template("servicios.html", servicios=servicios)
    except Exception as e:
        print(f"⚠️ Error en servicios: {e}")
        return render_template("servicios.html", servicios=[])

@app.route("/servicio/<int:id>")
def servicio_detalle(id):
    """Detalle de un servicio específico"""
    try:
        conn = get_db()
        servicio = conn.execute(
            'SELECT * FROM servicios WHERE id = ? AND activo = 1',
            (id,)
        ).fetchone()
        conn.close()
        
        if servicio:
            return render_template("servicio_detalle.html", servicio=servicio)
        else:
            flash('Servicio no encontrado', 'error')
            return redirect('/servicios')
    except Exception as e:
        print(f"⚠️ Error en servicio_detalle: {e}")
        flash('Error al cargar el servicio', 'error')
        return redirect('/servicios')

# ===============================
# RUTAS DE PROYECTOS
# ===============================

@app.route("/proyectos")
def proyectos():
    """Página de proyectos"""
    try:
        conn = get_db()
        
        # Verificar si la tabla proyectos existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proyectos'")
        if not cursor.fetchone():
            conn.close()
            return render_template("proyectos.html", 
                                 proyectos=[],
                                 total=0,
                                 en_progreso=0,
                                 completados=0)
        
        # Obtener filtros
        estado_filter = request.args.get('estado', '')
        
        # Construir consulta
        query = 'SELECT * FROM proyectos WHERE activo = 1'
        params = []
        
        if estado_filter:
            query += ' AND estado = ?'
            params.append(estado_filter)
        
        query += ' ORDER BY fecha_inicio DESC'
        
        proyectos = conn.execute(query, params).fetchall()
        
        # Obtener estadísticas
        total = len(proyectos)
        en_progreso = len([p for p in proyectos if p['estado'] == 'en_progreso'])
        completados = len([p for p in proyectos if p['estado'] == 'completado'])
        
        conn.close()
        
        return render_template("proyectos.html", 
                             proyectos=proyectos,
                             total=total,
                             en_progreso=en_progreso,
                             completados=completados,
                             estado_filter=estado_filter)
    except Exception as e:
        print(f"⚠️ Error en proyectos: {e}")
        return render_template("proyectos.html", proyectos=[])

@app.route("/proyecto/<int:id>")
def proyecto_detalle(id):
    """Detalle de un proyecto específico"""
    try:
        conn = get_db()
        proyecto = conn.execute(
            'SELECT * FROM proyectos WHERE id = ? AND activo = 1',
            (id,)
        ).fetchone()
        conn.close()
        
        if proyecto:
            return render_template("proyecto_detalle.html", proyecto=proyecto)
        else:
            flash('Proyecto no encontrado', 'error')
            return redirect('/proyectos')
    except Exception as e:
        print(f"⚠️ Error en proyecto_detalle: {e}")
        flash('Error al cargar el proyecto', 'error')
        return redirect('/proyectos')

# ===============================
# RUTAS DE AVISOS
# ===============================

@app.route("/avisos")
def avisos():
    """Página de avisos"""
    try:
        conn = get_db()
        
        # Verificar si la tabla avisos existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='avisos'")
        if not cursor.fetchone():
            conn.close()
            return render_template("avisos.html", 
                                 avisos=[],
                                 tipos=[],
                                 tipo_filter='')
        
        # Obtener filtros
        tipo_filter = request.args.get('tipo', '')
        
        # Construir consulta
        query = '''SELECT * FROM avisos 
                   WHERE activo = 1 
                   AND (fecha_expiracion IS NULL OR fecha_expiracion >= DATE('now'))'''
        params = []
        
        if tipo_filter:
            query += ' AND tipo = ?'
            params.append(tipo_filter)
        
        query += ' ORDER BY importante DESC, fecha_publicacion DESC'
        
        avisos_list = conn.execute(query, params).fetchall()
        
        # Obtener tipos únicos para el filtro
        try:
            tipos = conn.execute(
                'SELECT DISTINCT tipo FROM avisos WHERE activo = 1 ORDER BY tipo'
            ).fetchall()
        except:
            tipos = []
        
        conn.close()
        
        return render_template("avisos.html", 
                             avisos=avisos_list,
                             tipos=tipos,
                             tipo_filter=tipo_filter)
    except Exception as e:
        print(f"⚠️ Error en avisos: {e}")
        return render_template("avisos.html", avisos=[])

@app.route("/aviso/<int:id>")
def aviso_detalle(id):
    """Detalle de un aviso específico"""
    try:
        conn = get_db()
        aviso = conn.execute(
            '''SELECT * FROM avisos 
               WHERE id = ? AND activo = 1 
               AND (fecha_expiracion IS NULL OR fecha_expiracion >= DATE('now'))''',
            (id,)
        ).fetchone()
        conn.close()
        
        if aviso:
            return render_template("aviso_detalle.html", aviso=aviso)
        else:
            flash('Aviso no encontrado o expirado', 'error')
            return redirect('/avisos')
    except Exception as e:
        print(f"⚠️ Error en aviso_detalle: {e}")
        flash('Error al cargar el aviso', 'error')
        return redirect('/avisos')

# ===============================
# RUTAS DE PÁGINAS ESTÁTICAS
# ===============================

@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    """Página de contacto"""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        asunto = request.form.get("asunto", "").strip()
        mensaje = request.form.get("mensaje", "").strip()
        
        if not nombre or not email or not asunto or not mensaje:
            flash('Por favor complete todos los campos obligatorios', 'error')
            return render_template("contacto.html")
        
        try:
            conn = get_db()
            
            conn.execute(
                '''INSERT INTO contactos (nombre, email, telefono, asunto, mensaje)
                   VALUES (?, ?, ?, ?, ?)''',
                (nombre, email, telefono, asunto, mensaje)
            )
            
            conn.commit()
            conn.close()
            
            flash('¡Mensaje enviado correctamente! Nos pondremos en contacto pronto.', 'success')
            return redirect('/contacto')
            
        except Exception as e:
            print(f"❌ Error en contacto: {str(e)}")
            flash('Error al enviar el mensaje', 'error')
    
    return render_template("contacto.html")

@app.route("/nosotros")
def nosotros():
    """Página nosotros"""
    return render_template("nosotros.html")

@app.route("/transparencia")
def transparencia():
    """Página transparencia"""
    return render_template("transparencia.html")

# ===============================
# RUTAS DE ADMINISTRACIÓN
# ===============================

@app.route("/admin")
@admin_required
def admin_dashboard():
    """Panel de administración"""
    try:
        conn = get_db()
        
        # Estadísticas generales
        stats = {}
        
        try:
            stats['total_usuarios'] = conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
        except:
            stats['total_usuarios'] = 0
            
        try:
            stats['total_reportes'] = conn.execute('SELECT COUNT(*) FROM reportes').fetchone()[0]
        except:
            stats['total_reportes'] = 0
            
        try:
            stats['reportes_pendientes'] = conn.execute("SELECT COUNT(*) FROM reportes WHERE estado = 'pendiente'").fetchone()[0]
        except:
            stats['reportes_pendientes'] = 0
            
        try:
            stats['total_denuncias'] = conn.execute('SELECT COUNT(*) FROM denuncias').fetchone()[0]
        except:
            stats['total_denuncias'] = 0
            
        try:
            stats['denuncias_revision'] = conn.execute("SELECT COUNT(*) FROM denuncias WHERE estado = 'en_revision'").fetchone()[0]
        except:
            stats['denuncias_revision'] = 0
            
        try:
            stats['total_contactos'] = conn.execute('SELECT COUNT(*) FROM contactos WHERE estado = "nuevo"').fetchone()[0]
        except:
            stats['total_contactos'] = 0
        
        # Reportes recientes
        reportes_recientes = []
        try:
            reportes_recientes = conn.execute(
                '''SELECT r.*, u.nombre as usuario_nombre 
                   FROM reportes r 
                   JOIN usuarios u ON r.usuario_id = u.id 
                   ORDER BY r.fecha_reporte DESC LIMIT 10'''
            ).fetchall()
        except:
            pass
        
        # Usuarios recientes
        usuarios_recientes = []
        try:
            usuarios_recientes = conn.execute(
                'SELECT * FROM usuarios ORDER BY creado_en DESC LIMIT 10'
            ).fetchall()
        except:
            pass
        
        conn.close()
        
        return render_template("admin.html", 
                             stats=stats,
                             reportes_recientes=reportes_recientes,
                             usuarios_recientes=usuarios_recientes)
    except Exception as e:
        print(f"❌ Error en admin_dashboard: {str(e)}")
        flash('Error al cargar el panel de administración', 'error')
        return redirect('/')

@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    """Gestión de usuarios"""
    try:
        conn = get_db()
        
        # Obtener filtros
        rol_filter = request.args.get('rol', '')
        search = request.args.get('search', '')
        
        # Construir consulta
        query = 'SELECT * FROM usuarios WHERE 1=1'
        params = []
        
        if rol_filter:
            query += ' AND rol_id = ?'
            params.append(rol_filter)
        
        if search:
            query += ' AND (nombre LIKE ? OR email LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        
        query += ' ORDER BY creado_en DESC'
        
        usuarios = conn.execute(query, params).fetchall()
        
        conn.close()
        
        return render_template("admin_usuarios.html", 
                             usuarios=usuarios,
                             rol_filter=rol_filter,
                             search=search)
    except Exception as e:
        print(f"❌ Error en admin_usuarios: {str(e)}")
        flash('Error al cargar los usuarios', 'error')
        return redirect('/admin')

@app.route("/admin/usuarios/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def admin_editar_usuario(id):
    """Editar usuario"""
    try:
        conn = get_db()
        
        if request.method == "POST":
            nombre = request.form.get("nombre", "").strip()
            email = request.form.get("email", "").strip().lower()
            telefono = request.form.get("telefono", "").strip()
            rol_id = request.form.get("rol_id", "2")
            activo = 1 if request.form.get("activo") else 0
            
            # Verificar si el email ya existe (excluyendo el usuario actual)
            existe = conn.execute(
                'SELECT id FROM usuarios WHERE email = ? AND id != ?',
                (email, id)
            ).fetchone()
            
            if existe:
                flash('Este correo electrónico ya está registrado', 'error')
                usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (id,)).fetchone()
                conn.close()
                return render_template("admin_editar_usuario.html", usuario=usuario)
            
            conn.execute(
                '''UPDATE usuarios SET nombre = ?, email = ?, telefono = ?, 
                   rol_id = ?, activo = ? WHERE id = ?''',
                (nombre, email, telefono, rol_id, activo, id)
            )
            
            conn.commit()
            conn.close()
            
            flash('Usuario actualizado correctamente', 'success')
            return redirect('/admin/usuarios')
        
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (id,)).fetchone()
        conn.close()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect('/admin/usuarios')
        
        return render_template("admin_editar_usuario.html", usuario=usuario)
        
    except Exception as e:
        print(f"❌ Error en admin_editar_usuario: {str(e)}")
        flash('Error al editar el usuario', 'error')
        return redirect('/admin/usuarios')

@app.route("/admin/reportes")
@admin_required
def admin_reportes():
    """Gestión de reportes"""
    try:
        conn = get_db()
        
        # Verificar si la tabla reportes existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reportes'")
        if not cursor.fetchone():
            conn.close()
            return render_template("admin_reportes.html", 
                                 reportes=[],
                                 categorias=[],
                                 estado_filter='',
                                 categoria_filter='',
                                 prioridad_filter='')
        
        # Obtener filtros
        estado_filter = request.args.get('estado', '')
        categoria_filter = request.args.get('categoria', '')
        prioridad_filter = request.args.get('prioridad', '')
        
        # Construir consulta
        query = '''SELECT r.*, u.nombre as usuario_nombre 
                   FROM reportes r 
                   JOIN usuarios u ON r.usuario_id = u.id 
                   WHERE 1=1'''
        params = []
        
        if estado_filter:
            query += ' AND r.estado = ?'
            params.append(estado_filter)
        
        if categoria_filter:
            query += ' AND r.categoria = ?'
            params.append(categoria_filter)
        
        if prioridad_filter:
            query += ' AND r.prioridad = ?'
            params.append(prioridad_filter)
        
        query += ' ORDER BY r.fecha_reporte DESC'
        
        reportes = conn.execute(query, params).fetchall()
        
        # Obtener categorías únicas para el filtro
        categorias = []
        try:
            categorias = conn.execute(
                'SELECT DISTINCT categoria FROM reportes ORDER BY categoria'
            ).fetchall()
        except:
            pass
        
        conn.close()
        
        return render_template("admin_reportes.html", 
                             reportes=reportes,
                             categorias=categorias,
                             estado_filter=estado_filter,
                             categoria_filter=categoria_filter,
                             prioridad_filter=prioridad_filter)
    except Exception as e:
        print(f"❌ Error en admin_reportes: {str(e)}")
        flash('Error al cargar los reportes', 'error')
        return redirect('/admin')

@app.route("/admin/reportes/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def admin_editar_reporte(id):
    """Editar reporte"""
    try:
        conn = get_db()
        
        if request.method == "POST":
            estado = request.form.get("estado", "").strip()
            respuesta_admin = request.form.get("respuesta_admin", "").strip()
            
            conn.execute(
                '''UPDATE reportes SET estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                   WHERE id = ?''',
                (estado, id)
            )
            
            # Si hay respuesta, agregar como comentario del admin
            if respuesta_admin:
                try:
                    conn.execute(
                        '''INSERT INTO comentarios (reporte_id, usuario_id, contenido, tipo)
                           VALUES (?, ?, ?, ?)''',
                        (id, session['user_id'], respuesta_admin, 'respuesta_admin')
                    )
                except:
                    pass
            
            conn.commit()
            conn.close()
            
            flash('Reporte actualizado correctamente', 'success')
            return redirect('/admin/reportes')
        
        reporte = conn.execute(
            '''SELECT r.*, u.nombre as usuario_nombre 
               FROM reportes r 
               JOIN usuarios u ON r.usuario_id = u.id 
               WHERE r.id = ?''',
            (id,)
        ).fetchone()
        
        conn.close()
        
        if not reporte:
            flash('Reporte no encontrado', 'error')
            return redirect('/admin/reportes')
        
        return render_template("admin_editar_reporte.html", reporte=reporte)
        
    except Exception as e:
        print(f"❌ Error en admin_editar_reporte: {str(e)}")
        flash('Error al editar el reporte', 'error')
        return redirect('/admin/reportes')

@app.route("/admin/denuncias")
@admin_required
def admin_denuncias():
    """Gestión de denuncias"""
    try:
        conn = get_db()
        
        # Verificar si la tabla denuncias existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='denuncias'")
        if not cursor.fetchone():
            conn.close()
            return render_template("admin_denuncias.html", 
                                 denuncias=[],
                                 estado_filter='',
                                 tipo_filter='')
        
        # Obtener filtros
        estado_filter = request.args.get('estado', '')
        tipo_filter = request.args.get('tipo', '')
        
        # Construir consulta
        query = '''SELECT d.*, u.nombre as usuario_nombre 
                   FROM denuncias d 
                   JOIN usuarios u ON d.usuario_id = u.id 
                   WHERE 1=1'''
        params = []
        
        if estado_filter:
            query += ' AND d.estado = ?'
            params.append(estado_filter)
        
        if tipo_filter:
            query += ' AND d.tipo = ?'
            params.append(tipo_filter)
        
        query += ' ORDER BY d.fecha_denuncia DESC'
        
        denuncias = conn.execute(query, params).fetchall()
        
        conn.close()
        
        return render_template("admin_denuncias.html", 
                             denuncias=denuncias,
                             estado_filter=estado_filter,
                             tipo_filter=tipo_filter)
    except Exception as e:
        print(f"❌ Error en admin_denuncias: {str(e)}")
        flash('Error al cargar las denuncias', 'error')
        return redirect('/admin')

@app.route("/admin/denuncias/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def admin_editar_denuncia(id):
    """Editar denuncia"""
    try:
        conn = get_db()
        
        if request.method == "POST":
            estado = request.form.get("estado", "").strip()
            observaciones = request.form.get("observaciones", "").strip()
            
            conn.execute(
                '''UPDATE denuncias SET estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                   WHERE id = ?''',
                (estado, id)
            )
            
            conn.commit()
            conn.close()
            
            flash('Denuncia actualizada correctamente', 'success')
            return redirect('/admin/denuncias')
        
        denuncia = conn.execute(
            '''SELECT d.*, u.nombre as usuario_nombre 
               FROM denuncias d 
               JOIN usuarios u ON d.usuario_id = u.id 
               WHERE d.id = ?''',
            (id,)
        ).fetchone()
        
        conn.close()
        
        if not denuncia:
            flash('Denuncia no encontrada', 'error')
            return redirect('/admin/denuncias')
        
        return render_template("admin_editar_denuncia.html", denuncia=denuncia)
        
    except Exception as e:
        print(f"❌ Error en admin_editar_denuncia: {str(e)}")
        flash('Error al editar la denuncia', 'error')
        return redirect('/admin/denuncias')

@app.route("/admin/contactos")
@admin_required
def admin_contactos():
    """Gestión de contactos"""
    try:
        conn = get_db()
        
        # Verificar si la tabla contactos existe
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contactos'")
        if not cursor.fetchone():
            conn.close()
            return render_template("admin_contactos.html", 
                                 contactos=[],
                                 estado_filter='')
        
        # Obtener filtros
        estado_filter = request.args.get('estado', '')
        
        # Construir consulta
        query = 'SELECT * FROM contactos WHERE 1=1'
        params = []
        
        if estado_filter:
            query += ' AND estado = ?'
            params.append(estado_filter)
        
        query += ' ORDER BY fecha DESC'
        
        contactos = conn.execute(query, params).fetchall()
        
        conn.close()
        
        return render_template("admin_contactos.html", 
                             contactos=contactos,
                             estado_filter=estado_filter)
    except Exception as e:
        print(f"❌ Error en admin_contactos: {str(e)}")
        flash('Error al cargar los contactos', 'error')
        return redirect('/admin')

@app.route("/admin/contactos/<int:id>/responder", methods=["POST"])
@admin_required
def admin_responder_contacto(id):
    """Responder a un contacto"""
    try:
        respuesta = request.form.get("respuesta", "").strip()
        
        if not respuesta:
            flash('La respuesta no puede estar vacía', 'error')
            return redirect('/admin/contactos')
        
        conn = get_db()
        
        conn.execute(
            '''UPDATE contactos SET respuesta = ?, estado = 'respondido' 
               WHERE id = ?''',
            (respuesta, id)
        )
        
        conn.commit()
        conn.close()
        
        flash('Respuesta enviada correctamente', 'success')
        
    except Exception as e:
        print(f"❌ Error en admin_responder_contacto: {str(e)}")
        flash('Error al enviar la respuesta', 'error')
    
    return redirect('/admin/contactos')

# ===============================
# RUTAS PARA EXPORTACIÓN DE DATOS
# ===============================

@app.route("/admin/exportar/<tipo>")
@admin_required
def exportar_datos(tipo):
    """Exportar datos a CSV"""
    try:
        conn = get_db()
        
        if tipo == 'usuarios':
            data = conn.execute('SELECT * FROM usuarios').fetchall()
            filename = 'usuarios.csv'
            fields = ['id', 'nombre', 'email', 'telefono', 'cedula', 'rol_id', 'creado_en']
        
        elif tipo == 'reportes':
            data = conn.execute('''
                SELECT r.*, u.nombre as usuario_nombre 
                FROM reportes r 
                JOIN usuarios u ON r.usuario_id = u.id
            ''').fetchall()
            filename = 'reportes.csv'
            fields = ['id', 'usuario_nombre', 'titulo', 'descripcion', 'categoria', 'ubicacion', 'estado', 'fecha_reporte']
        
        elif tipo == 'denuncias':
            data = conn.execute('''
                SELECT d.*, u.nombre as usuario_nombre 
                FROM denuncias d 
                JOIN usuarios u ON d.usuario_id = u.id
            ''').fetchall()
            filename = 'denuncias.csv'
            fields = ['id', 'usuario_nombre', 'titulo', 'tipo', 'estado', 'fecha_denuncia']
        
        else:
            flash('Tipo de exportación no válido', 'error')
            return redirect('/admin')
        
        # Crear CSV en memoria
        output = BytesIO()
        writer = csv.writer(output)
        
        # Escribir encabezados
        writer.writerow(fields)
        
        # Escribir datos
        for row in data:
            writer.writerow([row[field] for field in fields])
        
        output.seek(0)
        
        conn.close()
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error en exportar_datos: {str(e)}")
        flash('Error al exportar los datos', 'error')
        return redirect('/admin')

# ===============================
# API ENDPOINTS
# ===============================

@app.route("/api/check-email")
def check_email():
    """Verificar si un email está disponible"""
    email = request.args.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'available': False, 'message': 'Email requerido'})
    
    try:
        conn = get_db()
        usuario = conn.execute(
            'SELECT id FROM usuarios WHERE email = ?',
            (email,)
        ).fetchone()
        conn.close()
        
        if usuario:
            return jsonify({'available': False, 'message': 'Email ya registrado'})
        else:
            return jsonify({'available': True, 'message': 'Email disponible'})
    except Exception as e:
        print(f"⚠️ Error en check_email: {e}")
        return jsonify({'available': False, 'message': 'Error al verificar email'})

@app.route("/api/estadisticas")
def api_estadisticas():
    """Obtener estadísticas del sistema"""
    try:
        conn = get_db()
        
        stats = {}
        
        try:
            stats['total_usuarios'] = conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
        except:
            stats['total_usuarios'] = 0
            
        try:
            stats['total_reportes'] = conn.execute('SELECT COUNT(*) FROM reportes').fetchone()[0]
        except:
            stats['total_reportes'] = 0
            
        try:
            stats['reportes_pendientes'] = conn.execute("SELECT COUNT(*) FROM reportes WHERE estado = 'pendiente'").fetchone()[0]
        except:
            stats['reportes_pendientes'] = 0
            
        try:
            stats['reportes_resueltos'] = conn.execute("SELECT COUNT(*) FROM reportes WHERE estado = 'resuelto'").fetchone()[0]
        except:
            stats['reportes_resueltos'] = 0
            
        try:
            stats['total_denuncias'] = conn.execute('SELECT COUNT(*) FROM denuncias').fetchone()[0]
        except:
            stats['total_denuncias'] = 0
            
        try:
            stats['total_proyectos'] = conn.execute('SELECT COUNT(*) FROM proyectos').fetchone()[0]
        except:
            stats['total_proyectos'] = 0
        
        conn.close()
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"❌ Error en api_estadisticas: {str(e)}")
        return jsonify({'error': str(e)})

# ===============================
# DEBUG ROUTE - PARA VER ESTRUCTURA DE BD
# ===============================

@app.route("/debug/db-structure")
def debug_db_structure():
    """Verificar estructura completa de la BD"""
    try:
        conn = get_db()
        
        print("\n" + "="*60)
        print("🔍 DEBUG: ESTRUCTURA COMPLETA DE LA BASE DE DATOS")
        print("="*60)
        
        # Listar todas las tablas
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        
        for tabla in tablas:
            tabla_nombre = tabla[0]
            print(f"\n📊 Tabla: {tabla_nombre}")
            print("-" * 40)
            
            # Mostrar columnas de cada tabla
            cursor = conn.execute(f"PRAGMA table_info({tabla_nombre})")
            columnas = cursor.fetchall()
            
            for col in columnas:
                print(f"  {col[1]} ({col[2]}) - PK: {col[5]}")
        
        conn.close()
        
        return jsonify({"message": "Estructura mostrada en consola"})
        
    except Exception as e:
        print(f"❌ Error en debug: {str(e)}")
        return jsonify({"error": str(e)})

# ===============================
# CONTEXT PROCESSORS
# ===============================

@app.context_processor
def inject_user():
    """Inyectar información del usuario en todos los templates"""
    user_data = {}
    
    if 'user_id' in session:
        user_data = {
            'id': session.get('user_id'),
            'nombre': session.get('user_name'),
            'email': session.get('user_email'),
            'rol_id': session.get('user_role', 2),
            'is_authenticated': True,
            'is_admin': session.get('user_role', 2) == 1
        }
    else:
        user_data = {
            'is_authenticated': False,
            'is_admin': False
        }
    
    return {
        'current_user': user_data,
        'current_year': datetime.now().year,
        'now': datetime.now()
    }

# ===============================
# MANEJO DE ERRORES
# ===============================

@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def acceso_denegado(error):
    flash('Acceso denegado. No tiene permisos para acceder a esta página.', 'error')
    return redirect('/')

@app.errorhandler(500)
def error_servidor(error):
    print(f"🔥 Error 500: {error}")
    return render_template('500.html'), 500

@app.errorhandler(413)
def archivo_demasiado_grande(error):
    flash('El archivo es demasiado grande. El tamaño máximo es 16MB.', 'error')
    return redirect(request.referrer or '/')

# ===============================
# INICIALIZACIÓN Y EJECUCIÓN
# ===============================

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("🚀 SISTEMA AYUNTAMIENTO DE CUTUPÚ - VERSIÓN COMPLETA")
    print("="*60)
    
    # Crear carpeta de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(f"📁 Carpeta de uploads creada: {app.config['UPLOAD_FOLDER']}")
    
    # Verificar y preparar base de datos
    if not verificar_y_preparar_db():
        print("\n❌ ERROR: Problema con la base de datos")
        print("="*60)
        exit(1)
    
    print(f"\n🔑 INFORMACIÓN DE ACCESO:")
    print(f"   1. Para ADMIN:")
    print(f"      Email: {ADMIN_EMAIL}")
    print(f"      Contraseña: admin123")
    print(f"   2. También puedes registrar una cuenta nueva")
    print("="*60)
    
    print("\n✅ Sistema listo para ejecutar")
    print("🌐 URL: http://localhost:5000")
    print("="*60)

    # ARRANCAR SERVIDOR FLASK
    app.run(debug=True, host="0.0.0.0", port=5000)
