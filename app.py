import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, abort
import os
from jinja2.exceptions import TemplateNotFound

app = Flask(__name__)
# GÜVENLİK UYARISI: secret_key'i doğrudan koda yazmak yerine ortam değişkenlerinden (environment variable) almak daha güvenlidir.
app.secret_key = os.environ.get('SECRET_KEY', 'varsayilan-guvenli-bir-anahtar-gelistirme-icin')

DATABASE_NAME = "veritabani.db"

# Sepet bilgileri, kullanıcı giriş yaptığında hafızada tutulacak.
carts = {}


# carts formatı: { user_id: [ { 'name': ..., 'price': ..., 'image': ..., 'quantity': ... }, ... ] }

def get_db_connection():
    """Veritabanı bağlantısı oluşturur ve satırları sözlük gibi erişilebilir yapar."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    # Eğer kullanıcı zaten giriş yapmışsa ana sayfaya yönlendir
    if 'user_id' in session:
        return redirect(url_for('ev'))
    return render_template('giriş_yap.html')  # Değilse giriş sayfasına


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return "E-posta ve şifre gerekli", 400

        try:
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO users (email, password) VALUES (?, ?)",
                    (email, password)
                )
                conn.commit()
        except sqlite3.IntegrityError:
            return "Bu e-posta adresi zaten kayıtlı, lütfen farklı bir e-posta seçin.", 400

        # Başarılı kayıt sonrası giriş sayfasına yönlendir
        return redirect(url_for('login'))
    return render_template('kayıt_ol.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['email'] = user['email']
            return redirect(url_for('ev'))
        else:
            return "Kimlik Bilgileri Geçersiz", 401
    return render_template('giriş_yap.html')


@app.route('/ev')
def ev():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('ev.html')


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    product_name = request.form.get('name')
    product_price = float(request.form.get('price'))
    product_image = request.form.get('image')
    quantity = int(request.form.get('quantity', 1))
    redirect_to_buy = request.form.get('buy_now')  # "Hemen Al" butonu için özel parametre

    cart = carts.get(user_id, [])

    # Ürün sepette zaten var mı diye kontrol et
    for item in cart:
        if item['name'] == product_name:
            item['quantity'] += quantity
            break
    else:  # for döngüsü break olmadan biterse (ürün sepette yoksa) çalışır
        cart.append({'name': product_name, 'price': product_price, 'image': product_image, 'quantity': quantity})

    carts[user_id] = cart

    # Eğer formdan "buy_now" parametresi geldiyse, satın alma sayfasına yönlendir.
    if redirect_to_buy:
        return redirect(url_for('buy'))

    return redirect(request.referrer or url_for('ev'))  # Kullanıcıyı geldiği sayfaya veya ana sayfaya geri yönlendir.


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    product_name_to_remove = request.form.get('product_name')

    cart = carts.get(user_id, [])

    # Ürünü listeden çıkar
    new_cart = [item for item in cart if item['name'] != product_name_to_remove]

    carts[user_id] = new_cart

    return redirect(url_for('sepet'))


@app.route('/sepet')
def sepet():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart = carts.get(user_id, [])
    total_price = sum(item['price'] * item['quantity'] for item in cart)

    return render_template('sepet.html', cart=cart, total_price=total_price)


@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart = carts.get(user_id, [])

    # Sepet boşsa satın alma sayfasına gitmesini engelle
    if not cart:
        return redirect(url_for('ev'))

    if request.method == 'POST':
        # --- ÖDEME SİMÜLASYONU ---
        # GERÇEK BİR UYGULAMADA KREDİ KARTI BİLGİLERİ ASLA BU ŞEKİLDE ALINMAZ, İŞLENMEZ VEYA SAKLANMAZ.
        # Bu kısım sadece formun dolu olup olmadığını kontrol eder ve bir ödeme adımını taklit eder.
        # Gerçek bir entegrasyon için Iyzico, Stripe gibi bir ödeme sağlayıcısı kullanılmalıdır.
        card_name = request.form.get('cardUser')
        card_number = request.form.get('cardNumber')
        card_expiry = request.form.get('cardExpiry')
        card_ccv = request.form.get('cardCCV')

        # Basit bir doğrulama: Tüm alanlar dolu mu?
        if not all([card_name, card_number, card_expiry, card_ccv]):
            total_price = sum(item['price'] * item['quantity'] for item in cart)
            return render_template(
                'satın_al.html',
                cart=cart,
                total_price=total_price,
                error="Lütfen tüm kart bilgilerini eksiksiz girin."
            )

        # Simülasyon başarılı kabul edildi, şimdi adres bilgilerini istemek için yönlendir.
        return redirect(url_for('siparis_onay'))

    # GET isteği ile gelinirse, satın alma sayfasını göster.
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    return render_template('satın_al.html', cart=cart, total_price=total_price)


@app.route('/siparis_onay', methods=['GET', 'POST'])
def siparis_onay():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart = carts.get(user_id, [])

    if not cart:
        # Adres sayfasına sepetsiz gelinirse ana sayfaya yönlendir
        return redirect(url_for('ev'))

    if request.method == 'POST':
        address = request.form.get('address')
        if not address:
            return render_template('siparis_onay.html', error="Lütfen bir adres girin veya haritadan seçin.")

        try:
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET adres = ? WHERE id = ?", (address, user_id))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Adres güncellenirken hata oluştu: {e}")
            return "Adresiniz güncellenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.", 500

        # Sipariş tamamlandı, sepeti temizle
        carts[user_id] = []
        return render_template('siparis_tamamlandi.html')

    # GET isteği ile gelinirse, kullanıcının mevcut adresini veritabanından çekip formu dolduralım.
    current_address = ''
    try:
        with get_db_connection() as conn:
            user = conn.execute("SELECT adres FROM users WHERE id = ?", (user_id,)).fetchone()
            if user and user['adres']:
                current_address = user['adres']
    except sqlite3.Error as e:
        print(f"Kullanıcı adresi çekilirken hata oluştu: {e}")

    return render_template('siparis_onay.html', current_address=current_address)


@app.route('/product/<product_page_name>')
def product_detail(product_page_name):
    """Dinamik olarak ürün detay sayfalarını gösterir."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        # Örneğin, /product/iphone16promax isteği geldiğinde templates/iphone16promax.html dosyasını render eder.
        return render_template(f'{product_page_name}.html')
    except TemplateNotFound:
        # Eğer ilgili HTML dosyası 'templates' klasöründe bulunamazsa 404 hatası verir.
        abort(404)


if __name__ == '__main__':
    app.run(debug=True)