import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect("cutupu.db")
cursor = conn.cursor()

# Consultar usuarios
cursor.execute("SELECT * FROM usuarios")
usuarios = cursor.fetchall()

print("\nUSUARIOS REGISTRADOS")
print("=" * 40)

for usuario in usuarios:
    print(usuario)

conn.close()