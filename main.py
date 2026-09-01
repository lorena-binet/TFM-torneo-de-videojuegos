import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from db import session, engine, Base
from models import Usuario, Juego
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename
import random

app = Flask(__name__)
app.secret_key = "clave_secreta_torneo"

# --- CONFIGURACIÓN DE CARPETAS ---
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'perfiles')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- CONFIGURACIÓN DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return session.query(Usuario).get(int(user_id))


# --- RUTAS DE NAVEGACIÓN PRINCIPAL ---

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('panel_torneo'))
    return redirect(url_for('login'))


@app.route("/panel")
@login_required
def panel_torneo():
    # 1. Ranking Global (Top 10)
    top_jugadores = session.query(Usuario).order_by(Usuario.puntos.desc()).limit(10).all()

    # 2. Ranking Dinámico por Juego
    todos_los_juegos = session.query(Juego).all()

    rankings_por_juego = {}
    for juego in todos_los_juegos:
        top_especifico = session.query(Usuario).filter_by(juego_seleccionado=juego.titulo).order_by(
            Usuario.puntos.desc()).limit(10).all()
        rankings_por_juego[juego.titulo] = top_especifico

    return render_template("index.html",
                           top_jugadores=top_jugadores,
                           rankings_por_juego=rankings_por_juego,
                           juegos_lista=todos_los_juegos)


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        nuevo_nombre = request.form.get("nombre")
        if nuevo_nombre:
            current_user.nombre = nuevo_nombre
            session.commit()
            return {"status": "ok"}, 200

    ranking_data = session.query(Usuario).filter(Usuario.juego_seleccionado != None).order_by(
        Usuario.puntos.desc()).all()
    return render_template("perfil.html", ranking_data=ranking_data)


@app.route("/explorar_torneos")
@login_required
def lista_juegos():
    # Solo mostramos juegos donde es_default sea estrictamente False
    juegos = session.query(Juego).filter(Juego.es_default == False).all()
    return render_template("lista_juegos.html", juegos=juegos)


@app.route("/torneo/<nombre_juego>")
@login_required
def detalles_juego(nombre_juego):
    nombre_limpio = nombre_juego.lower().replace(" ", "_")

    plantillas_especiales = {
        'valorant': 'torneo_valorant.html',
        'league_of_legends': 'torneo_league_of_legends.html',
        'apex_legends': 'torneo_apex_legends.html'
    }

    if nombre_limpio in plantillas_especiales:
        return render_template(plantillas_especiales[nombre_limpio])

    juego_db = session.query(Juego).filter_by(titulo=nombre_juego).first()
    return render_template("detalles_generico.html", juego=juego_db)


@app.route("/inscribir/<nombre_juego>", methods=["POST", "GET"])
@login_required
def inscribir_juego(nombre_juego):
    user = session.query(Usuario).get(current_user.id)

    # Traducción para asegurar que se guarde el nombre oficial
    traducciones = {
        'valorant': 'Valorant',
        'league_of_legends': 'League of Legends',
        'apex_legends': 'Apex Legends',
        'lol': 'League of Legends'
    }

    nombre_oficial = traducciones.get(nombre_juego, nombre_juego)
    user.juego_seleccionado = nombre_oficial

    if request.method == "POST":
        user.nivel = request.form.get("rango") or request.form.get("nivel")
        user.rol = request.form.get("rol")

    session.commit()
    flash(f"Inscrito en {nombre_oficial}")
    return redirect(url_for('panel_torneo'))


# --- RUTAS DE CUENTA (REGISTRO / LOGIN / FOTO / ELIMINAR) ---

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        avatares_defaults = ["default1.png", "default2.png", "default3.png"]
        foto_asignada = random.choice(avatares_defaults)

        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password=password,
            foto_perfil=foto_asignada
        )

        session.add(nuevo_usuario)
        session.commit()
        return redirect(url_for('login'))
    return render_template("registro.html")


@app.route('/subir_foto', methods=['POST'])
@login_required
def subir_foto():
    if 'foto' not in request.files:
        return redirect(request.url)
    file = request.files['foto']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = secure_filename(f"user_{current_user.id}_{file.filename}")
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        current_user.foto_perfil = filename
        session.commit()

    return redirect(url_for('perfil'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identificador = request.form.get("email")
        password = request.form.get("password")

        usuario = session.query(Usuario).filter(
            or_(Usuario.email == identificador, Usuario.nombre == identificador)
        ).first()

        if usuario and usuario.password == password:
            login_user(usuario)
            if usuario.es_admin:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('panel_torneo'))
        else:
            return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/eliminar_mi_cuenta', methods=['POST'])
@login_required
def eliminar_mi_cuenta():
    user = session.query(Usuario).get(current_user.id)
    session.delete(user)
    session.commit()
    logout_user()
    return redirect(url_for('login'))


# --- RUTAS DE ADMINISTRACIÓN ---

@app.route("/admin")
@login_required
def admin_panel():
    if not current_user.es_admin:
        return "Acceso denegado", 403

    # Agrupación en Python para evitar errores de compatibilidad SQL (evita el error de 'case')
    usuarios_con_juego = session.query(Usuario).filter(Usuario.juego_seleccionado != None).all()
    stats = {}
    for u in usuarios_con_juego:
        # Si el usuario tiene 'lol', lo sumamos a 'League of Legends' en la gráfica
        j = "League of Legends" if u.juego_seleccionado == 'lol' else u.juego_seleccionado
        stats[j] = stats.get(j, 0) + 1

    labels = list(stats.keys())
    data = list(stats.values())

    juegos = session.query(Juego).all()
    usuarios_participantes = session.query(Usuario).filter(Usuario.juego_seleccionado != None).all()
    todos_los_usuarios = session.query(Usuario).all()

    return render_template("admin.html",
                           usuarios=usuarios_participantes,
                           todos_los_usuarios=todos_los_usuarios,
                           juegos=juegos,
                           labels=labels,
                           data=data)


@app.route("/admin/editar_juego/<int:id>", methods=["POST"])
@login_required
def editar_juego(id):
    if not current_user.es_admin: return "No autorizado", 403
    juego = session.query(Juego).get(id)
    if juego:
        juego.titulo = request.form.get("titulo")
        juego.descripcion = request.form.get("descripcion")
        session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/editar_puntos/<int:id>', methods=['POST'])
@login_required
def editar_puntos(id):
    if not current_user.es_admin:
        return {"error": "No autorizado"}, 403

    usuario = session.query(Usuario).get(id)
    nuevos_puntos = request.form.get('puntos')

    if usuario and nuevos_puntos is not None:
        usuario.puntos = int(nuevos_puntos)
        session.commit()
        return {"puntos": usuario.puntos}, 200
    return {"error": "Error"}, 400


@app.route("/admin/editar_participante/<int:id>", methods=["POST"])
@login_required
def editar_participante(id):
    if not current_user.es_admin: return "No autorizado", 403

    user = session.query(Usuario).get(id)
    if user:
        user.nivel = request.form.get("nivel")
        user.rol = request.form.get("rol")
        session.commit()

    return redirect(url_for('admin_panel'))


@app.route("/admin/eliminar_usuario/<int:id>")
@login_required
def eliminar_usuario(id):
    if not current_user.es_admin: return "No autorizado", 403
    user = session.query(Usuario).get(id)
    if user:
        user.juego_seleccionado = None
        user.nivel = None
        user.rol = None
        session.commit()
    return redirect(url_for('admin_panel'))


@app.route("/admin/nuevo_juego", methods=["POST"])
@login_required
def crear_juego():
    if not current_user.es_admin: return "No autorizado", 403
    titulo = request.form.get("titulo")
    if titulo:
        nuevo = Juego(titulo=titulo, descripcion=request.form.get("descripcion"))
        session.add(nuevo)
        session.commit()
    return redirect(url_for('admin_panel'))


@app.route("/admin/eliminar_juego/<int:id>")
@login_required
def eliminar_juego(id):
    if not current_user.es_admin: return "No autorizado", 403
    juego = session.query(Juego).get(id)
    if juego:
        session.delete(juego)
        session.commit()
    return redirect(url_for('admin_panel'))


if __name__ == "__main__":
    Base.metadata.create_all(engine)

    if __name__ == "__main__":
        Base.metadata.create_all(engine)

        with app.app_context():
            # 1. Aseguramos que los juegos base existan y sean 'default'
            juegos_base = [
                {"titulo": "Valorant", "plataforma": "PC"},
                {"titulo": "League of Legends", "plataforma": "PC"},
                {"titulo": "Apex Legends", "plataforma": "PC"}
            ]

            for j_data in juegos_base:
                juego = session.query(Juego).filter_by(titulo=j_data["titulo"]).first()
                if not juego:
                    nuevo_juego = Juego(
                        titulo=j_data["titulo"],
                        es_default=True
                    )
                    session.add(nuevo_juego)
                else:
                    juego.es_default = True

            session.commit()

        app.run(debug=True)