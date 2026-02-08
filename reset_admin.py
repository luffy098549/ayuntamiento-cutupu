# reset_admin.py
import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('cutupu.db')
cursor = conn.cursor()

print("🔄 RESETEANDO CONTRASEÑA DEL ADMIN...")

# Obtener ID del admin
cursor.execute("SELECT id FROM usuarios WHERE email = 'admin@ayuntamiento.gob'")
result = cursor.fetchone()

if result:
    admin_id = result[0]
    print(f"✅ Admin encontrado con ID: {admin_id}")
    
    # Generar NUEVO hash con contraseña simple
    new_password = "admin123"
    new_hash = generate_password_hash(new_password)
    
    # Actualizar en la BD
    cursor.execute(
        "UPDATE usuarios SET password_hash = ? WHERE id = ?",
        (new_hash, admin_id)
    )
    
    conn.commit()
    print(f"✅ Contraseña actualizada a: {new_password}")
    
else:
    print("❌ Admin no encontrado, creando uno nuevo...")
    new_password = "admin123"
    new_hash = generate_password_hash(new_password)
    
    cursor.execute('''
        INSERT INTO usuarios (nombre, email, password_hash, rol_id, creado_en, activo)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
    ''', ('Administrador', 'admin@ayuntamiento.gob', new_hash, 1, 1))
    
    conn.commit()
    print(f"✅ Nuevo admin creado con contraseña: {new_password}")

conn.close()

print(f"""
========================================
✅ OPERACIÓN COMPLETADA

Credenciales para iniciar sesión:
  📧 Email: admin@ayuntamiento.gob
  🔑 Contraseña: admin123

💡 Ahora ve a http://localhost:5000/login
   e ingresa estas credenciales.
========================================
""")