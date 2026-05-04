# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, json, time
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'aeroapex_mx_2024_secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aeroapex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER']     = 'static/img/productos'
app.config['CAT_FOLDER']        = 'static/img/categorias'
app.config['BANNER_FOLDER']     = 'static/img/banners'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB
WHATSAPP = '573180517417'
ALLOWED  = {'png','jpg','jpeg','webp','gif'}

db = SQLAlchemy(app)
for f in [app.config['UPLOAD_FOLDER'], app.config['CAT_FOLDER'], app.config['BANNER_FOLDER']]:
    os.makedirs(f, exist_ok=True)

def allowed(fn): return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED

def save_file(file, folder):
    if file and file.filename and allowed(file.filename):
        fn = f"{int(time.time())}_{secure_filename(file.filename)}"
        file.save(os.path.join(folder, fn))
        return fn
    return None

# ══ MODELOS ══════════════════════════════
class Categoria(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(80), nullable=False)
    slug        = db.Column(db.String(80), unique=True)
    descripcion = db.Column(db.String(300), default='')
    imagen      = db.Column(db.String(200), default='')
    icono       = db.Column(db.String(10),  default='🏍️')
    orden       = db.Column(db.Integer,     default=0)
    activa      = db.Column(db.Boolean,     default=True)
    productos   = db.relationship('Producto', backref='cat_rel', lazy=True)

class Producto(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(120), nullable=False)
    descripcion  = db.Column(db.Text,   default='')
    precio       = db.Column(db.Float,  nullable=False)
    precio_antes = db.Column(db.Float,  default=0)
    stock        = db.Column(db.Integer,default=0)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=True)
    imagen       = db.Column(db.String(200), default='')
    destacado    = db.Column(db.Boolean, default=False)
    nuevo        = db.Column(db.Boolean, default=False)
    proximamente = db.Column(db.Boolean, default=False)
    activo       = db.Column(db.Boolean, default=True)
    creado       = db.Column(db.DateTime, default=datetime.utcnow)


class ProductoImagen(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    producto_id= db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    imagen     = db.Column(db.String(200), nullable=False)
    orden      = db.Column(db.Integer, default=0)
    producto   = db.relationship('Producto', backref='imagenes_extra', lazy=True)

class SeccionImagen(db.Model):
    id     = db.Column(db.Integer, primary_key=True)
    seccion= db.Column(db.String(60), unique=True)
    imagen = db.Column(db.String(200), default='')
    titulo = db.Column(db.String(120), default='')
    subtitulo = db.Column(db.String(200), default='')

class BannerSlide(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    titulo   = db.Column(db.String(120), default='')
    subtitulo= db.Column(db.String(200), default='')
    imagen   = db.Column(db.String(200), default='')
    link     = db.Column(db.String(200), default='')
    orden    = db.Column(db.Integer,     default=0)
    activo   = db.Column(db.Boolean,     default=True)

class Config(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(60), unique=True)
    valor = db.Column(db.Text, default='')

class SectionImage(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    seccion  = db.Column(db.String(60), unique=True)
    imagen   = db.Column(db.String(200), default='')
    titulo   = db.Column(db.String(120), default='')


class MediaItem(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    titulo      = db.Column(db.String(120), default='')
    tipo        = db.Column(db.String(10),  default='video')
    archivo     = db.Column(db.String(200), default='')
    descripcion = db.Column(db.String(300), default='')
    orden       = db.Column(db.Integer,     default=0)
    activo      = db.Column(db.Boolean,     default=True)
    creado      = db.Column(db.DateTime,    default=datetime.utcnow)

class Admin(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    usuario  = db.Column(db.String(60), unique=True)
    password = db.Column(db.String(200))

def gcfg(k, default=''):
    c = Config.query.filter_by(clave=k).first()
    return c.valor if c else default

def scfg(k, v):
    from sqlalchemy.orm.attributes import flag_modified
    c = Config.query.filter_by(clave=k).first()
    if c:
        c.valor = str(v)
        flag_modified(c, 'valor')
    else:
        db.session.add(Config(clave=k, valor=str(v)))
    db.session.commit()

def login_req(f):
    @wraps(f)
    def d(*a,**kw):
        if not session.get('admin'): return redirect(url_for('admin_login'))
        return f(*a,**kw)
    return d

@app.context_processor
def ctx():
    cats   = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    wsp    = gcfg('whatsapp', WHATSAPP)
    ann    = gcfg('ann', '🏍️ ENVÍOS GRATIS EN BOGOTÁ · ACCESORIOS PREMIUM PARA TU MOTO')
    slides = BannerSlide.query.filter_by(activo=True).order_by(BannerSlide.orden).all()
    get_sec = lambda k: (SeccionImagen.query.filter_by(seccion=k).first() or type('',(),{'imagen':''})()).imagen
    return dict(nav_cats=cats, WHATSAPP=wsp, ANN=ann, slides=slides, gcfg=gcfg, get_sec=get_sec)

# ══ TIENDA PÚBLICA ════════════════════════
@app.route('/')
def index():
    cats       = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    destacados = Producto.query.filter_by(destacado=True, activo=True, proximamente=False).limit(8).all()
    nuevos     = Producto.query.filter_by(nuevo=True,     activo=True, proximamente=False).limit(4).all()
    prox       = Producto.query.filter_by(proximamente=True, activo=True).limit(6).all()
    return render_template('index.html', cats=cats, destacados=destacados,
                           nuevos=nuevos, prox=prox)

@app.route('/catalogo')
def catalogo():
    q     = request.args.get('q','')
    sort  = request.args.get('sort','nuevo')
    cid   = request.args.get('cat',0,type=int)
    query = Producto.query.filter_by(activo=True, proximamente=False)
    if q:   query = query.filter(Producto.nombre.ilike(f'%{q}%'))
    if cid: query = query.filter_by(categoria_id=cid)
    if sort=='precio_asc':   query = query.order_by(Producto.precio.asc())
    elif sort=='precio_desc':query = query.order_by(Producto.precio.desc())
    elif sort=='destacado':  query = query.filter_by(destacado=True)
    else:                    query = query.order_by(Producto.creado.desc())
    prods = query.all()
    cats  = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    return render_template('catalogo.html', prods=prods, cats=cats,
                           q=q, sort=sort, cid=cid)

@app.route('/categoria/<int:cid>')
def categoria(cid):
    cat   = Categoria.query.get_or_404(cid)
    sort  = request.args.get('sort','nuevo')
    q     = request.args.get('q','')
    query = Producto.query.filter_by(categoria_id=cid, activo=True, proximamente=False)
    if q: query = query.filter(Producto.nombre.ilike(f'%{q}%'))
    if sort=='precio_asc':   query = query.order_by(Producto.precio.asc())
    elif sort=='precio_desc':query = query.order_by(Producto.precio.desc())
    else:                    query = query.order_by(Producto.creado.desc())
    prods = query.all()
    cats  = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    return render_template('categoria.html', cat=cat, prods=prods,
                           cats=cats, sort=sort, q=q)

@app.route('/producto/<int:pid>')
def producto(pid):
    p    = Producto.query.get_or_404(pid)
    rel  = Producto.query.filter_by(categoria_id=p.categoria_id, activo=True)               .filter(Producto.id!=pid, Producto.proximamente==False).limit(4).all()
    cats = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    return render_template('producto.html', p=p, rel=rel, cats=cats)


@app.route('/media')
def media_page():
    items = MediaItem.query.filter_by(activo=True).order_by(MediaItem.orden).all()
    cats  = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    return render_template('media.html', items=items, cats=cats)

@app.route('/info')
def info():
    cats = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    info_cfg = {k: gcfg(k,v) for k,v in {
        'info_envio_bogota':   'Realizamos envíos GRATIS dentro de Bogotá.',
        'info_envio_nacional': 'Para envíos a nivel nacional el costo varía según la ciudad y el peso del pedido.',
        'info_como_comprar':   'Elige tu producto, haz clic en Pedir por WhatsApp, confirmamos disponibilidad y coordinamos el envío.',
        'info_garantia':       'Todos nuestros productos son 100% originales. Garantía contra defectos de fabricación.',
        'info_pagos':          'Transferencia bancaria, Nequi, Daviplata, Efectivo (Bogotá).',
        'info_sobre_nosotros': 'Somos una marca colombiana especializada en accesorios de lujo para motociclistas.',
        'info_faq':            '¿Tienen tienda física? Solo venta online por ahora.',
    }.items()}
    return render_template('info.html', cats=cats, info_cfg=info_cfg)

@app.route('/proximamente')
def proximamente():
    prods = Producto.query.filter_by(proximamente=True, activo=True).all()
    cats  = Categoria.query.filter_by(activa=True).order_by(Categoria.orden).all()
    return render_template('proximamente.html', prods=prods, cats=cats)

# ══ ADMIN ════════════════════════════════
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    err = None
    if request.method=='POST':
        a = Admin.query.filter_by(usuario=request.form['usuario']).first()
        if a and check_password_hash(a.password, request.form['password']):
            session['admin']=True; session['admin_u']=a.usuario
            return redirect(url_for('admin_dash'))
        err='Credenciales incorrectas.'
    return render_template('admin/login.html', err=err)

@app.route('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('admin_login'))

@app.route('/admin')
@login_req
def admin_dash():
    st = {
        'prods':    Producto.query.count(),
        'cats':     Categoria.query.count(),
        'activos':  Producto.query.filter_by(activo=True).count(),
        'sin_stock':Producto.query.filter(Producto.stock==0, Producto.activo==True).count(),
        'prox':     Producto.query.filter_by(proximamente=True).count(),
    }
    rec = Producto.query.order_by(Producto.creado.desc()).limit(8).all()
    return render_template('admin/dashboard.html', st=st, rec=rec)

# CATEGORÍAS
@app.route('/admin/categorias')
@login_req
def adm_cats():
    return render_template('admin/categorias.html', cats=Categoria.query.order_by(Categoria.orden).all())

@app.route('/admin/categorias/<action>', methods=['GET','POST'], defaults={'cid':0})
@app.route('/admin/categorias/<action>/<int:cid>', methods=['GET','POST'])
@login_req
def adm_cat(action, cid):
    cat = Categoria.query.get(cid) if cid else None
    if request.method=='POST':
        if action=='eliminar':
            db.session.delete(cat); db.session.commit()
            flash('Categoría eliminada.','info')
            return redirect(url_for('adm_cats'))
        fn = save_file(request.files.get('imagen'), app.config['CAT_FOLDER'])
        nombre = request.form['nombre']
        import re
        slug = re.sub(r'[^a-z0-9]+','-', nombre.lower().strip())
        if cat:
            if fn: cat.imagen = f'img/categorias/{fn}'
            cat.nombre=nombre; cat.slug=slug
            cat.descripcion=request.form.get('descripcion','')
            cat.icono=request.form.get('icono','🏍️')
            cat.orden=int(request.form.get('orden',0))
            cat.activa='activa' in request.form
        else:
            cat = Categoria(nombre=nombre, slug=slug,
                descripcion=request.form.get('descripcion',''),
                icono=request.form.get('icono','🏍️'),
                orden=int(request.form.get('orden',0)),
                imagen=f'img/categorias/{fn}' if fn else '',
                activa='activa' in request.form)
            db.session.add(cat)
        db.session.commit()
        flash('Categoría guardada.','success')
        return redirect(url_for('adm_cats'))
    return render_template('admin/form_cat.html', cat=cat, action=action)

# PRODUCTOS
@app.route('/admin/productos')
@login_req
def adm_prods():
    cid   = request.args.get('cat',0,type=int)
    query = Producto.query
    if cid: query=query.filter_by(categoria_id=cid)
    prods = query.order_by(Producto.creado.desc()).all()
    cats  = Categoria.query.order_by(Categoria.orden).all()
    return render_template('admin/productos.html', prods=prods, cats=cats, cid=cid)

@app.route('/admin/productos/<action>', methods=['GET','POST'], defaults={'pid':0})
@app.route('/admin/productos/<action>/<int:pid>', methods=['GET','POST'])
@login_req
def adm_prod(action, pid):
    p    = Producto.query.get(pid) if pid else None
    cats = Categoria.query.filter_by(activa=True).all()
    if request.method=='POST':
        if action=='eliminar':
            db.session.delete(p); db.session.commit()
            flash('Producto eliminado.','info')
            return redirect(url_for('adm_prods'))
        fn   = save_file(request.files.get('imagen'), app.config['UPLOAD_FOLDER'])
        cid  = request.form.get('categoria_id') or None
        data = dict(
            nombre=request.form['nombre'],
            descripcion=request.form.get('descripcion',''),
            precio=float(request.form['precio']),
            precio_antes=float(request.form.get('precio_antes') or 0),
            stock=int(request.form.get('stock',0)),
            categoria_id=int(cid) if cid else None,
            destacado='destacado' in request.form,
            nuevo='nuevo' in request.form,
            proximamente='proximamente' in request.form,
            activo='activo' in request.form
        )
        if p:
            for k,v in data.items(): setattr(p,k,v)
            if fn: p.imagen=f'img/productos/{fn}'
        else:
            p = Producto(**data, imagen=f'img/productos/{fn}' if fn else '')
            db.session.add(p)
        db.session.commit()
        flash('Producto guardado.','success')
        return redirect(url_for('adm_prods'))
    return render_template('admin/form_prod.html', p=p, cats=cats, action=action)

# BANNERS
@app.route('/admin/banners')
@login_req
def adm_banners():
    return render_template('admin/banners.html', slides=BannerSlide.query.order_by(BannerSlide.orden).all())

@app.route('/admin/banners/<action>', methods=['GET','POST'], defaults={'bid':0})
@app.route('/admin/banners/<action>/<int:bid>', methods=['GET','POST'])
@login_req
def adm_banner(action, bid):
    b = BannerSlide.query.get(bid) if bid else None
    if request.method=='POST':
        if action=='eliminar':
            db.session.delete(b); db.session.commit(); flash('Banner eliminado.','info')
            return redirect(url_for('adm_banners'))
        fn = save_file(request.files.get('imagen'), app.config['BANNER_FOLDER'])
        if b:
            if fn: b.imagen=f'img/banners/{fn}'
            b.titulo=request.form.get('titulo',''); b.subtitulo=request.form.get('subtitulo','')
            b.link=request.form.get('link',''); b.orden=int(request.form.get('orden',0))
            b.activo='activo' in request.form
        else:
            b=BannerSlide(titulo=request.form.get('titulo',''),subtitulo=request.form.get('subtitulo',''),
                link=request.form.get('link',''),orden=int(request.form.get('orden',0)),
                imagen=f'img/banners/{fn}' if fn else '',activo='activo' in request.form)
            db.session.add(b)
        db.session.commit(); flash('Banner guardado.','success')
        return redirect(url_for('adm_banners'))
    return render_template('admin/form_banner.html', b=b, action=action)

# CONFIG
@app.route('/admin/config', methods=['GET','POST'])
@login_req
def adm_config():
    if request.method=='POST':
        for k in ['whatsapp','ann','email','instagram','tiktok','facebook','envio_texto','dark_mode']:
            scfg(k, request.form.get(k,''))
        flash('Configuración guardada.','success')
    cfg = {k: gcfg(k, v) for k,v in {
        'whatsapp': WHATSAPP, 'ann':'🏍️ ENVÍOS GRATIS EN BOGOTÁ',
        'email':'aeroapexmotorcycle@gmail.com',
        'instagram':'aeroapex.ridex','tiktok':'aeroapex.ridex',
        'facebook':'Aero Apex Moto',
        'envio_texto':'Envíos gratis en Bogotá. A nivel nacional con costo adicional.'
    }.items()}
    return render_template('admin/config.html', cfg=cfg)


@app.route('/admin/productos/imagenes/<int:pid>', methods=['GET','POST'])
@login_req
def adm_prod_imgs(pid):
    p = Producto.query.get_or_404(pid)
    if request.method=='POST':
        files = request.files.getlist('imagenes')
        for i, file in enumerate(files):
            fn = save_file(file, app.config['UPLOAD_FOLDER'])
            if fn:
                img = ProductoImagen(producto_id=pid, imagen=f'img/productos/{fn}', orden=i)
                db.session.add(img)
        db.session.commit()
        flash(f'Imágenes agregadas correctamente.','success')
        return redirect(url_for('adm_prod_imgs', pid=pid))
    imgs = ProductoImagen.query.filter_by(producto_id=pid).order_by(ProductoImagen.orden).all()
    return render_template('admin/prod_imagenes.html', p=p, imgs=imgs)

@app.route('/admin/productos/imagenes/eliminar/<int:iid>', methods=['POST'])
@login_req
def adm_del_img(iid):
    img = ProductoImagen.query.get_or_404(iid)
    pid = img.producto_id
    db.session.delete(img); db.session.commit()
    flash('Imagen eliminada.','info')
    return redirect(url_for('adm_prod_imgs', pid=pid))

@app.route('/admin/secciones', methods=['GET','POST'])
@login_req
def adm_secciones():
    SECCIONES = [
        ('hero', 'Hero / Banner principal', 1400, 600),
        ('cats_bg', 'Fondo de categorías', 1400, 800),
        ('brands_bg', 'Sección marcas compatibles', 1400, 600),
        ('prox_bg', 'Fondo próximamente', 1400, 500),
        ('info_bg', 'Fondo información', 1400, 500),
    ]
    if request.method=='POST':
        seccion = request.form.get('seccion')
        fn = save_file(request.files.get('imagen'), app.config['BANNER_FOLDER'])
        if fn:
            s = SeccionImagen.query.filter_by(seccion=seccion).first()
            if s: s.imagen = f'img/banners/{fn}'
            else: db.session.add(SeccionImagen(seccion=seccion, imagen=f'img/banners/{fn}'))
            db.session.commit()
            flash(f'Imagen de sección actualizada.','success')
        return redirect(url_for('adm_secciones'))
    secciones_data = []
    for key, nombre, w, h in SECCIONES:
        s = SeccionImagen.query.filter_by(seccion=key).first()
        secciones_data.append({'key':key,'nombre':nombre,'w':w,'h':h,'imagen':s.imagen if s else ''})
    return render_template('admin/secciones.html', secciones=secciones_data)



# SECTION IMAGES ADMIN

@app.route('/admin/secciones/<seccion>', methods=['GET','POST'])
@login_req
def adm_seccion(seccion):
    s = SectionImage.query.filter_by(seccion=seccion).first()
    if not s:
        s = SectionImage(seccion=seccion, titulo=seccion)
        db.session.add(s)
        db.session.commit()
    
    SIZES = {
        'hero': ('1400×500px', 'Banner principal de la página de inicio'),
        'categorias': ('600×400px', 'Imagen de fondo de la sección de categorías'),
        'destacados': ('cualquier tamaño', 'Fondo de la sección de destacados'),
        'proximamente': ('1400×500px', 'Imagen de fondo de la sección próximamente'),
        'marcas': ('1200×600px', 'Imagen de marcas compatibles'),
        'info': ('1400×400px', 'Imagen del hero de la página de información'),
    }
    size_info = SIZES.get(seccion, ('800×600px', 'Imagen de sección'))
    
    if request.method=='POST':
        fn = save_file(request.files.get('imagen'), app.config['BANNER_FOLDER'])
        if fn:
            s.imagen = f'img/banners/{fn}'
        s.titulo = request.form.get('titulo', s.titulo)
        db.session.commit()
        flash(f'Imagen de {seccion} actualizada.','success')
        return redirect(url_for('adm_secciones'))
    return render_template('admin/form_seccion.html', s=s, size_info=size_info)

# MULTI-IMAGE upload for products
@app.route('/admin/productos/imagenes/<int:pid>', methods=['POST'])
@login_req
def adm_prod_imagenes(pid):
    files = request.files.getlist('imagenes')
    orden = ProductoImagen.query.filter_by(producto_id=pid).count()
    for i, f in enumerate(files):
        fn = save_file(f, app.config['UPLOAD_FOLDER'])
        if fn:
            img = ProductoImagen(producto_id=pid, imagen=f'img/productos/{fn}', orden=orden+i)
            db.session.add(img)
    db.session.commit()
    flash('Imágenes adicionales guardadas.','success')
    return redirect(url_for('adm_prod', action='editar', pid=pid))

@app.route('/admin/productos/imagen-extra/eliminar/<int:pid>/<int:idx>', methods=['POST'])
@login_req
def adm_del_img_extra(pid, idx):
    imgs = ProductoImagen.query.filter_by(producto_id=pid).order_by(ProductoImagen.orden).all()
    if 0 <= idx < len(imgs):
        db.session.delete(imgs[idx])
        db.session.commit()
    flash('Imagen eliminada.','info')
    return redirect(url_for('adm_prod', action='editar', pid=pid))




@app.route('/design.css')
def design_css():
    from flask import Response
    accent  = gcfg('color_acento','#e60000')
    accent2 = gcfg('color_acento2','#ff4500')
    bg      = gcfg('color_fondo','#080808')
    card    = gcfg('color_tarjeta','#111111')
    text    = gcfg('color_texto','#f0f0f0')
    border  = gcfg('color_borde','#1e1e1e')
    btn_r   = gcfg('btn_radius','0px')
    btn_p   = gcfg('btn_padding','.65rem 1.6rem')
    btn_fs  = gcfg('btn_font_size','.95rem')
    btn_ls  = gcfg('btn_letter_spacing','.1em')
    btn_tt  = gcfg('btn_text_transform','uppercase')
    hero_h  = gcfg('hero_height','88vh')
    glow    = gcfg('glow_intensidad','35')
    spd     = gcfg('animacion_velocidad','.35')
    cat_h   = gcfg('cat_height','130px')
    cat_fs  = gcfg('cat_font_size','2.4rem')
    css = f"""
:root {{
  --red: {accent};
  --red2: {accent2};
  --dark: {bg};
  --dark2: {card};
  --white: {text};
  --border: {border};
  --btn-radius: {btn_r};
  --btn-padding: {btn_p};
  --btn-fs: {btn_fs};
  --btn-ls: {btn_ls};
  --btn-tt: {btn_tt};
  --hero-h: {hero_h};
  --glow: rgba(230,0,0,{int(glow)/100:.2f});
  --spd: {spd}s;
  --cat-h: {cat_h};
  --cat-fs: {cat_fs};
}}
.btn {{ border-radius:var(--btn-radius) !important; padding:var(--btn-padding) !important; font-size:var(--btn-fs) !important; letter-spacing:var(--btn-ls) !important; text-transform:var(--btn-tt) !important; }}
.btn-red {{ background:var(--red) !important; box-shadow:0 0 20px var(--glow) !important; }}
.btn-red:hover {{ background:var(--red2) !important; box-shadow:0 0 40px var(--glow) !important; }}
.cat-card {{ height:var(--cat-h) !important; }}
.cat-name {{ font-size:var(--cat-fs) !important; }}
.hero {{ min-height:var(--hero-h) !important; }}
"""
    return Response(css, mimetype='text/css')


@app.route('/admin/media')
@login_req
def adm_media():
    items = MediaItem.query.order_by(MediaItem.creado.desc()).all()
    return render_template('admin/media.html', items=items)

@app.route('/admin/media/nuevo', methods=['GET','POST'])
@login_req
def adm_media_nuevo():
    MEDIA_FOLDER = 'static/img/media'
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
    if request.method == 'POST':
        ALLOWED_M = {'mp4','webm','gif','jpg','jpeg','png','webp'}
        ffile = request.files.get('archivo')
        fn = None
        if ffile and ffile.filename and '.' in ffile.filename and ffile.filename.rsplit('.',1)[1].lower() in ALLOWED_M:
            import time as _t
            fn = f"{int(_t.time())}_{secure_filename(ffile.filename)}"
            ffile.save(os.path.join(MEDIA_FOLDER, fn))
        m = MediaItem(
            titulo=request.form.get('titulo',''),
            tipo=request.form.get('tipo','video'),
            archivo=f'img/media/{fn}' if fn else '',
            descripcion=request.form.get('descripcion',''),
            orden=int(request.form.get('orden',0)),
            activo='activo' in request.form
        )
        db.session.add(m); db.session.commit()
        flash('Media agregado.','success')
        return redirect(url_for('adm_media'))
    return render_template('admin/form_media.html', m=None)

@app.route('/admin/media/eliminar/<int:mid>', methods=['POST'])
@login_req
def adm_media_eliminar(mid):
    m = MediaItem.query.get_or_404(mid)
    db.session.delete(m); db.session.commit()
    flash('Media eliminado.','info')
    return redirect(url_for('adm_media'))

# ══ ADMIN — DISEÑO Y COLORES ════════════════════
@app.route('/admin/diseno', methods=['GET','POST'])
@login_req
def adm_diseno():
    if request.method == 'POST':
        keys = [
            'color_acento','color_acento2','color_fondo',
            'color_tarjeta','color_texto','color_borde',
            'btn_radius','btn_padding','btn_font_size',
            'btn_letter_spacing','btn_text_transform',
            'hero_height','font_display','font_body',
            'glow_intensidad','animacion_velocidad',
            'cat_height','cat_font_size',
        ]
        for k in keys:
            v = request.form.get(k,'')
            scfg(k, v)
        flash('Diseño actualizado. Recarga la tienda para ver los cambios.','success')
        return redirect(url_for('adm_diseno'))

    defaults = {
        'color_acento':         '#e60000',
        'color_acento2':        '#ff4500',
        'color_fondo':          '#080808',
        'color_tarjeta':        '#111111',
        'color_texto':          '#f0f0f0',
        'color_borde':          '#1e1e1e',
        'btn_radius':           '0px',
        'btn_padding':          '.65rem 1.6rem',
        'btn_font_size':        '.95rem',
        'btn_letter_spacing':   '.1em',
        'btn_text_transform':   'uppercase',
        'hero_height':          '88vh',
        'font_display':         "'Bebas Neue', sans-serif",
        'font_body':            "'Barlow', sans-serif",
        'glow_intensidad':      '35',
        'animacion_velocidad':  '.35',
        'cat_height':           '130px',
        'cat_font_size':        '2.4rem',
    }
    cfg = {k: gcfg(k, v) for k, v in defaults.items()}
    return render_template('admin/diseno.html', cfg=cfg)

# ══ ADMIN — PÁGINA DE INICIO ════════════════════
@app.route('/admin/pagina-inicio', methods=['GET','POST'])
@login_req
def adm_pagina_inicio():
    if request.method == 'POST':
        keys = ['hero_titulo','hero_subtitulo','hero_bajada',
                'stats_envio','stats_respuesta',
                'sec_destacados_titulo','sec_nuevos_titulo',
                'cta_titulo','cta_texto','cta_btn',
                'ann_texto','marquee_texto']
        for k in keys:
            v = request.form.get(k,'')
            scfg(k, v)
        flash('Página de inicio actualizada.','success')
        return redirect(url_for('adm_pagina_inicio'))

    cfg = {k: gcfg(k,v) for k,v in {
        'hero_titulo':          'DOMINA CADA CURVA',
        'hero_subtitulo':       'Accesorios de Lujo',
        'hero_bajada':          'Equípate con lo mejor. Accesorios premium para motociclistas que exigen calidad y estilo.',
        'stats_envio':          'FREE',
        'stats_respuesta':      '24h',
        'sec_destacados_titulo':'Productos Destacados',
        'sec_nuevos_titulo':    'Nuevos Ingresos',
        'cta_titulo':           '¿LISTO PARA EQUIPARTE?',
        'cta_texto':            'Contáctanos por WhatsApp y te asesoramos con tu pedido. Atención personalizada.',
        'cta_btn':              'ESCRIBIR POR WHATSAPP',
        'ann_texto':            gcfg('ann','🏍️ ENVÍOS GRATIS EN BOGOTÁ · ACCESORIOS PREMIUM PARA TU MOTO'),
        'marquee_texto':        'AERO APEX · ESPEJOS · PORTA PLACAS · SLIDERS · TAPA VÁLVULAS · GRIPS · POSAS PIE · INTERCOMUNICADORES',
    }.items()}
    return render_template('admin/pagina_inicio.html', cfg=cfg)

@app.route('/admin/pagina-info', methods=['GET','POST'])
@login_req
def adm_pagina_info():
    if request.method == 'POST':
        keys = ['info_hero_titulo','info_envio_bogota','info_envio_nacional',
                'info_como_comprar','info_garantia','info_pagos',
                'info_sobre_nosotros','info_faq']
        for k in keys:
            scfg(k, request.form.get(k,''))
        flash('Página de información actualizada.','success')
        return redirect(url_for('adm_pagina_info'))

    cfg = {k: gcfg(k,v) for k,v in {
        'info_hero_titulo':     'INFORMACIÓN',
        'info_envio_bogota':    'Realizamos envíos GRATIS dentro de Bogotá.',
        'info_envio_nacional':  'Para envíos a nivel nacional el costo varía según la ciudad y el peso del pedido.',
        'info_como_comprar':    'Elige tu producto, haz clic en Pedir por WhatsApp, confirmamos disponibilidad y coordinamos el envío.',
        'info_garantia':        'Todos nuestros productos son 100% originales. Garantía contra defectos de fabricación.',
        'info_pagos':           'Transferencia bancaria, Nequi, Daviplata, Efectivo (Bogotá).',
        'info_sobre_nosotros':  'Somos una marca colombiana especializada en accesorios de lujo para motociclistas.',
        'info_faq':             '¿Tienen tienda física? Solo venta online por ahora.',
    }.items()}
    return render_template('admin/pagina_info.html', cfg=cfg)

# ══ INIT ════════════════════════════
def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            db.session.add(Admin(usuario='admin', password=generate_password_hash('aeroapex2024')))
            CATS = [
                ('Espejos','🪞',1),('Porta Placas','🔩',2),('Sliders','🛡️',3),
                ('Tapa Valvulas','🔧',4),('Grips','🤜',5),('Pesas','⚖️',6),
                ('Posa Pie','👣',7),('Intercomunicadores','📡',8),
            ]
            for nombre,icono,orden in CATS:
                import re
                slug = re.sub(r'[^a-z0-9]+','-',nombre.lower())
                db.session.add(Categoria(nombre=nombre,slug=slug,icono=icono,orden=orden))
            # Default config
            defaults = {
                'whatsapp': WHATSAPP,
                'ann':'🏍️ ENVÍOS GRATIS EN BOGOTÁ · ACCESORIOS PREMIUM PARA TU MOTO',
                'email':'aeroapexmotorcycle@gmail.com',
                'instagram':'aeroapex.ridex','tiktok':'aeroapex.ridex',
                'facebook':'Aero Apex Moto',
                'envio_texto':'Realizamos envíos GRATIS dentro de Bogotá. Para envíos a nivel nacional el costo varía según la ciudad y el peso del pedido.',
        'dark_mode': '1'
            }
            for k,v in defaults.items():
                db.session.add(Config(clave=k, valor=v))
            db.session.commit()
            print("✅ BD Aero Apex lista · admin / aeroapex2024")


@app.errorhandler(413)
def too_large(e):
    flash('El archivo es demasiado grande. Máximo 200 MB.','info')
    return redirect(request.referrer or url_for('adm_media')), 413

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
