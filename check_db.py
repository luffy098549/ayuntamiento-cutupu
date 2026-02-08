import sqlite3
import os

db_file = 'cutupu.db'

if not os.path.exists(db_file):
    print(f"❌ Archivo {db_file} no encontrado")
    exit(1)

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

print("="*60)
print("🔍 ESTRUCTURA COMPLETA DE LA TABLA usuarios:")
print("="*60)

# Ver todas las columnas de la tabla usuarios
cursor.execute("PRAGMA table_info(usuarios)")
columnas = cursor.fetchall()

print("Columnas encontradas:")
for col in columnas:
    print(f"  → {col[1]} ({col[2]}) - PK: {col[5]}")
    print(f"    CID: {col[0]}, Not Null: {col[3]}, Default: {col[4]}")

print("\n" + "="*60)
print("👤 DATOS DE USUARIOS (primeras filas):")
print("="*60)

# Verificar qué datos hay
cursor.execute("SELECT * FROM usuarios LIMIT 5")
usuarios = cursor.fetchall()

if usuarios:
    # Obtener nombres de columnas
    cursor.execute("PRAGMA table_info(usuarios)")
    nombres_columnas = [col[1] for col in cursor.fetchall()]
    
    print("Columnas:", nombres_columnas)
    print("\nDatos:")
    for usuario in usuarios:
        for i, valor in enumerate(usuario):
            col_name = nombres_columnas[i] if i < len(nombres_columnas) else f"col{i}"
            print(f"  {col_name}: {valor}")
        print("-"*40)
else:
    print("❌ No hay usuarios en la tabla")

print("\n" + "="*60)
print("🔑 BUSCANDO COLUMNAS DE CONTRASEÑA:")
print("="*60)

# Buscar columnas que puedan ser contraseña
posibles_passwords = ['contrasena', 'clave', 'pass', 'password', 'contrasenia', 'clave_acceso']

for posible in posibles_passwords:
    # Verificar si existe columna con ese nombre
    cursor.execute(f"PRAGMA table_info(usuarios)")
    columnas = [col[1].lower() for col in cursor.fetchall()]
    
    if posible in columnas:
        print(f"✅ Posible columna de contraseña encontrada: '{posible}'")
        
        # Ver datos de esa columna
        cursor.execute(f"SELECT {posible} FROM usuarios LIMIT 3")
        datos = cursor.fetchall()
        print(f"  Valores ejemplo: {[d[0][:30] + '...' if d[0] and len(d[0]) > 30 else d[0] for d in datos]}")

conn.close()