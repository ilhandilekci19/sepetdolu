import sqlite3

DATABASE_NAME = "veritabani.db"

def create_tables():
    """Veritabanı bağlantısı oluşturur ve tabloları kurar/günceller."""
    # 'with' ifadesi, bağlantının ve imlecin otomatik olarak kapanmasını sağlar.
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()

            # Users tablosunu oluştur
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            """)

            # 'adres' sütununun varlığını kontrol et ve yoksa ekle
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'adres' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN adres TEXT")
                print("'adres' sütunu 'users' tablosuna eklendi.")

            print("Veritabanı ve 'users' tablosu başarıyla oluşturuldu/kontrol edildi.")
    except sqlite3.Error as e:
        print(f"Veritabanı hatası: {e}")

if __name__ == '__main__':
    create_tables()